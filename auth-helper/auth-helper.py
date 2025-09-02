#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import stat
import argparse
import subprocess
import re
import sys
from typing import Any, Dict, Optional

import requests
import msal


class AuthHelper:
    """
    단일 진입점 구조:
      - register-app  : Azure AD 앱 등록(+ 메타 저장)
      - init          : 토큰 유효성 검사 → 디바이스 코드 인증(필요 시) → 토큰 저장
      - status        : 현재 토큰 상태 출력
      - logout        : 토큰/캐시 삭제
      - set-tenant    : TENANT_ID 변경(옵션 또는 프롬프트)
    token.json 존재 여부와 상관없이 안전하게 동작하도록 분기 처리.
    """

    # token 파일에 유지하는 주요 키
    META_KEYS = {"CLIENT_ID", "TENANT_ID", "SCOPES"}
    TOKEN_KEYS = {
        "access_token", "refresh_token", "expires_in", "expires_on",
        "token_type", "scope", "id_token"
    }

    def __init__(self, token_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.token_path = token_path or os.path.join(base_dir, "../secrets/token.json")
        self._store: Dict[str, Any] = self._load_json(self.token_path) or {}

        # 메타 기본값
        self.tenant_id: str = self._store.get("TENANT_ID", "organizations")
        self.client_id: str = self._store.get("CLIENT_ID", "")
        scopes_raw = self._store.get("SCOPES", "Tasks.ReadWrite")
        self.scopes = self._normalize_scopes(scopes_raw)

        # MSAL 객체는 지연 생성
        self._app: Optional[msal.PublicClientApplication] = None
        
    def _get(self, key: str, default=None):
        """env → token store 순으로 설정값 조회"""
        import os
        return os.environ.get(key) or self._store.get(key, default)        

    # ---------------------------
    # 내부 유틸
    # ---------------------------
    def _normalize_scopes(self, scopes_val: Any):
        """
        scopes를 리스트로 정규화.
        openid/profile/offline_access는 제거(디바이스 플로우 기본 스코프 아님).
        """
        if isinstance(scopes_val, str):
            items = scopes_val.split()
        elif isinstance(scopes_val, list):
            items = list(scopes_val)
        else:
            items = ["Tasks.ReadWrite"]

        banned = {"offline_access", "openid", "profile"}
        return [s for s in items if s and s not in banned]

    def _load_json(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[경고] JSON 로드 실패({path}): {e}", flush=True)
        return None

    def _save_json(self, path: str, data: Dict[str, Any]):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _merge_store(self, update: Dict[str, Any]):
        """
        token.json 스토어에 안전 병합(메타는 유지, 토큰은 덮어씀).
        """
        self._store = self._store or {}
        self._store.update(update)
        self._save_json(self.token_path, self._store)

    def _ensure_token_file(self):
        """
        token.json이 없으면 메타 기본값 포함한 기본 구조로 생성.
        (빈 토큰 필드 포함, 권한도 600 부여)
        """
        if not os.path.exists(self.token_path):
            base = {
                "CLIENT_ID": self.client_id,
                "TENANT_ID": self.tenant_id,
                "SCOPES": " ".join(self.scopes),
                # 빈 토큰 형태
                "access_token": "",
                "refresh_token": "",
                "expires_on": 0,
                "expires_in": 0,
                "token_type": "Bearer",
                "scope": ""
            }
            self._save_json(self.token_path, base)
            self._store = base
            try:
                os.chmod(self.token_path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                print(f"[경고] token.json chmod 실패: {e}", flush=True)
            print("token.json 파일이 없어 기본 구조로 자동 생성했습니다.", flush=True)

    def _set_file_permissions(self):
        """
        token.json / session.secret 권한 600 적용(존재 시).
        """
        session_secret_path = os.path.join(os.path.dirname(self.token_path), "session.secret")
        if os.path.exists(self.token_path):
            try:
                os.chmod(self.token_path, stat.S_IRUSR | stat.S_IWUSR)
                print("token.json 및 인증 캐시 발급 완료 (서비스 컨테이너에는 마운트 금지)", flush=True)
            except Exception as e:
                print(f"token.json chmod 실패: {e}", flush=True)
        if os.path.exists(session_secret_path):
            try:
                os.chmod(session_secret_path, stat.S_IRUSR | stat.S_IWUSR)
                print("session.secret 및 인증 캐시 발급 완료 (서비스 컨테이너에는 마운트 금지)", flush=True)
            except Exception as e:
                print(f"session.secret chmod 실패: {e}", flush=True)

    def _get_app(self) -> msal.PublicClientApplication:
        """
        MSAL PublicClientApplication 인스턴스 보장.
        CLIENT_ID가 없으면 사용자가 register-app을 먼저 수행해야 함.
        """
        if self._app is not None:
            return self._app
        if not self.client_id:
            raise RuntimeError(
                "CLIENT_ID가 없습니다. 먼저 `register-app`을 실행해 앱을 등록하세요."
            )
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self._app = msal.PublicClientApplication(self.client_id, authority=authority)
        return self._app

    # ---------------------------
    # 토큰 저장/로드/검증
    # ---------------------------
    def save_token(self, token: Dict[str, Any]):
        """
        토큰과 메타를 함께 token.json에 저장.
        msal_token_cache.bin도 가능 시 저장.
        """
        # 기존 메타 유지
        meta = {k: self._store.get(k) for k in self.META_KEYS if k in self._store}
        # 토큰 필드만 추출해 병합
        token_only = {k: v for k, v in token.items() if k in self.TOKEN_KEYS}
        merged = {}
        merged.update(meta)
        merged.update(token_only)

        # scope가 응답에 있으면 string으로 들어오므로 그대로 보존
        if "SCOPES" not in merged:
            merged["SCOPES"] = " ".join(self.scopes)

        self._merge_store(merged)

        # msal 토큰 캐시 저장(가능 시)
        try:
            from msal import SerializableTokenCache
            cache = SerializableTokenCache()
            if "access_token" in token_only:
                cache.deserialize(json.dumps({"AccessToken": [token_only]}))
            cache_path = os.path.join(os.path.dirname(self.token_path), "msal_token_cache.bin")
            with open(cache_path, "w") as f:
                f.write(cache.serialize())
        except Exception as e:
            print(f"msal_token_cache.bin 저장 실패: {e}", flush=True)

    def load_token(self) -> Optional[Dict[str, Any]]:
        """
        token.json에서 토큰 필드만 반환(없으면 None).
        """
        if not self._store:
            self._store = self._load_json(self.token_path) or {}
        token = {k: self._store.get(k) for k in self.TOKEN_KEYS if k in self._store}
        if token.get("access_token"):
            return token
        return None

    def is_token_valid(self, token: Dict[str, Any]) -> bool:
        """
        1) 만료 검사(expires_on)
        2) Microsoft Graph /me 호출 검증
        """
        if not token or "access_token" not in token:
            print("[토큰 없음 또는 access_token 누락]", flush=True)
            return False

        now = int(time.time())
        try:
            expires_on = int(token.get("expires_on", 0))
        except Exception:
            expires_on = 0

        if expires_on and now > expires_on:
            print("[토큰 만료]", flush=True)
            return False

        try:
            headers = {"Authorization": f"Bearer {token['access_token']}"}
            resp = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers, timeout=5)
            if resp.status_code == 200:
                print("[토큰 실제 Azure API 검증: 성공]", flush=True)
                return True
            else:
                print(
                    f"[토큰 실제 Azure API 검증: 실패] status: {resp.status_code}, body: {resp.text}",
                    flush=True,
                )
                return False
        except Exception as e:
            print(f"[토큰 유효성 검증 오류] {e}", flush=True)
            return False

    # ---------------------------
    # 인증 플로우
    # ---------------------------
    def device_flow_auth(self) -> Optional[Dict[str, Any]]:
        app = self._get_app()
        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            print("Device flow initiation failed.", flush=True)
            return None

        print(f"[인증 코드] {flow['user_code']}", flush=True)
        print(f"[인증 URL] {flow['verification_uri']}", flush=True)
        print("브라우저에서 URL을 열고 코드를 입력하세요.", flush=True)

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            print("인증 성공!", flush=True)
            return result

        print("인증 실패:", result.get("error_description"), flush=True)
        return None

    def authenticate(self) -> bool:
        """
        토큰 파일 보장 → 권한 설정 → 기존 토큰 검증 → 필요 시 디바이스 코드 인증
        """
        self._ensure_token_file()
        self._set_file_permissions()

        print("--- 인증 자동화 시작 ---", flush=True)
        token = self.load_token()
        if token:
            print("[세션 감지] 기존 토큰 파일 존재", flush=True)
            if self.is_token_valid(token):
                print("[세션 유효] 실제 Azure API 검증까지 통과, 바로 사용 가능", flush=True)
                return True
            print("[세션 만료/유효하지 않음] 갱신 필요", flush=True)
        else:
            print("[세션 없음] 최초 인증 필요", flush=True)

        print("[인증/갱신 안내] 디바이스 코드 인증을 진행합니다.", flush=True)
        try:
            new_token = self.device_flow_auth()
        except RuntimeError as e:
            print(str(e), flush=True)
            return False

        if new_token and "access_token" in new_token:
            self.save_token(new_token)
            print("[세션 갱신] 인증 성공, 토큰 저장 완료", flush=True)
            return True

        print("[인증 실패] 토큰을 저장하지 못했습니다.", flush=True)
        return False

    # ---------------------------
    # Azure CLI 보조
    # ---------------------------
    def ensure_az_login(self) -> bool:
        """
        Azure CLI 로그인 보장. 미로그인 시 az login 수행.
        """
        try:
            out = subprocess.check_output(["az", "account", "show"], text=True)
            info = json.loads(out)
            if "user" in info or "id" in info:
                return True
        except Exception:
            print("[Azure 인증 필요] 컨테이너 최초 실행 시 브라우저에서 로그인합니다.", flush=True)
            subprocess.run(["az", "login"], check=True)
            return True
        return False

    # --- auth-helper.py: register_app() 함수만 교체 ---
    def register_app(self):
        
        self.ensure_az_login()
        """
        Microsoft Graph Delegated 권한(Tasks.ReadWrite)으로 퍼블릭 클라이언트 앱 생성.
        - 권한: Tasks.ReadWrite (Scope GUID: 2219042f-cab5-40cc-b0d2-16b1540b4c5f)
        - public client 활성화: --is-fallback-public-client
        - required-resource-accesses는 manifest 파일(@file)로 전달
        - 생성된 CLIENT_ID/TENANT_ID/SCOPES는 token.json 메타에 저장(self._merge_store)
        """
        import tempfile, time, json, subprocess, os

        app_name = f"{self._get('APP_PREFIX', 'mcp-todo-server')}-{int(time.time())}"

        graph_app_id = "00000003-0000-0000-c000-000000000000"  # Microsoft Graph
        tasks_readwrite_scope = "2219042f-cab5-40cc-b0d2-16b1540b4c5f"  # Delegated Scope

        manifest = [{
            "resourceAppId": graph_app_id,
            "resourceAccess": [
                {"id": tasks_readwrite_scope, "type": "Scope"},
                # 필요 시 로그인 기본 권한(Delegated User.Read)도 추가 가능:
                # {"id": "e1fe6dd8-ba31-4d61-89e7-88639da4683d", "type": "Scope"}
            ]
        }]

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmpf:
            json.dump(manifest, tmpf)
            tmpf.flush()
            manifest_path = tmpf.name

        try:
            print(f"[Azure 앱 등록] {app_name}", flush=True)
            create_cmd = [
                "az", "ad", "app", "create",
                "--display-name", app_name,
                "--is-fallback-public-client",
                "--required-resource-accesses", f"@{manifest_path}",
            ]
            create_json = json.loads(subprocess.check_output(create_cmd, text=True))
            client_id = create_json.get("appId")
            object_id = create_json.get("id")

            # 진단(옵션)
            try:
                show_out = subprocess.check_output(
                    ["az", "ad", "app", "show", "--id", object_id], text=True
                )
                print(f"[진단] az ad app show 결과:\n{show_out}", flush=True)
            except subprocess.CalledProcessError as e:
                print(f"[진단] az ad app show 실패: {e}", flush=True)

            # 현재 로그인 컨텍스트의 tenantId 확인
            try:
                tenant_id = subprocess.check_output(
                    ["az", "account", "show", "--query", "tenantId", "-o", "tsv"], text=True
                ).strip()
            except Exception:
                tenant_id = self.tenant_id

            # 메타 저장은 _merge_store로 직접(메타키 보존)
            self._merge_store({
                "CLIENT_ID": client_id,
                "TENANT_ID": tenant_id,
                "SCOPES": "Tasks.ReadWrite",
            })
            # MSAL 앱 재생성 대비
            self.client_id = client_id
            self.tenant_id = tenant_id
            self.scopes = self._normalize_scopes("Tasks.ReadWrite")
            self._app = None  # lazy 재생성

            print(f"CLIENT_ID={client_id}", flush=True)
            print(f"TENANT_ID={tenant_id}", flush=True)
            print("SCOPES=Tasks.ReadWrite", flush=True)
            print("[완료] 앱 등록 및 메타 저장 완료", flush=True)
            return client_id, tenant_id, "Tasks.ReadWrite"

        finally:
            try:
                os.remove(manifest_path)
            except Exception:
                pass
    

    # ---------------------------
    # 상태/로그아웃/테넌트 변경
    # ---------------------------
    def status(self):
        token = self.load_token()
        if token and "access_token" in token:
            exp = token.get("expires_on")
            try:
                exp_human = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(exp))) if exp else "unknown"
            except Exception:
                exp_human = "unknown"
            print(f"현재 인증됨. 만료(로컬): {exp_human}", flush=True)
        else:
            print("인증 정보 없음.", flush=True)

    def logout(self):
        removed = False
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
            removed = True
        cache_path = os.path.join(os.path.dirname(self.token_path), "msal_token_cache.bin")
        if os.path.exists(cache_path):
            os.remove(cache_path)
            removed = True
        print("인증 정보 삭제됨." if removed else "삭제할 인증 정보 없음.", flush=True)

    def set_tenant(self, new_tenant: Optional[str] = None):
        """
        TENANT_ID 변경:
          - 우선순위: 인자 > 환경변수 TENANT_ID > 프롬프트
        변경 후 MSAL 앱 재생성.
        """
        tenant = new_tenant or os.environ.get("TENANT_ID")
        if not tenant:
            tenant = input("설정할 TENANT_ID를 입력하세요 (예: organizations 또는 GUID): ").strip()

        if not tenant:
            print("TENANT_ID가 유효하지 않습니다.", flush=True)
            return

        if not re.match(r"^[0-9a-zA-Z-]+$|^[0-9a-fA-F-]{36}$", tenant):
            print("TENANT_ID 형식이 올바르지 않습니다.", flush=True)
            return

        self.tenant_id = tenant
        self._merge_store({"TENANT_ID": tenant})
        self._app = None
        try:
            self._get_app()
        except RuntimeError:
            # CLIENT_ID가 없을 수 있음 → 이후 register-app 필요
            pass
        print(f"TENANT_ID가 '{tenant}'(으)로 설정되었습니다.", flush=True)

    # ---------------------------
    # CLI 라우터
    # ---------------------------
    def run_cmd(self, argv: Optional[list] = None):
        parser = argparse.ArgumentParser(description="AuthHelper CLI")
        sub = parser.add_subparsers(dest="cmd")

        sub.add_parser("init")
        sub.add_parser("status")
        sub.add_parser("logout")
        sub.add_parser("register-app")

        p_set = sub.add_parser("set-tenant")
        p_set.add_argument("--tenant", help="변경할 TENANT_ID(미지정 시 환경변수→프롬프트 순)")

        # 기본: init
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
        cmd = args.cmd or "init"

        if cmd == "init":
            ok = self.authenticate()
            sys.exit(0 if ok else 1)
        elif cmd == "status":
            self.status()
        elif cmd == "logout":
            self.logout()
        elif cmd == "register-app":
            self.register_app()
        elif cmd == "set-tenant":
            self.set_tenant(getattr(args, "tenant", None))
        else:
            parser.print_help()
            
            
            


def main():
    helper = AuthHelper()
    helper.run_cmd()


if __name__ == "__main__":
    main()
