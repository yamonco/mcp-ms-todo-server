#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auth-helper (modular): config/graph/dbsync/tokens/appreg/cli 로 분리된 엔트리 포인트.
패키지명이 하이픈을 포함해 상대임포트 대신 로컬 모듈 임포트를 사용합니다.
"""
import sys
import os

# ensure current directory on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli  # type: ignore

if __name__ == "__main__":
    raise SystemExit(cli.main())
        try:
            url = f"{self.mcp_url}/admin/tokens/by-profile/{self.token_profile}"
            r = requests.get(url, headers={"x-api-key": self.master_key}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return {
                    "tenant_id": data.get("tenant_id"),
                    "client_id": data.get("client_id"),
                    "scopes": data.get("scopes"),
                }
        except Exception as e:
            print(f"[DB] meta fetch 실패: {e}", flush=True)
        return None
    def _db_get_token(self) -> Optional[Dict[str, Any]]:
        if not (self.store_mode == "db" and self.master_key and self.token_profile):
            return None
        try:
            url = f"{self.mcp_url}/admin/tokens/by-profile/{self.token_profile}"
            r = requests.get(url, headers={"x-api-key": self.master_key}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Prefer raw if present
                return data.get("raw") or {
                    k: data.get(k) for k in [
                        "access_token", "refresh_token", "expires_on", "expires_in", "token_type", "scope"
                    ]
                }
        except Exception as e:
            print(f"[DB] token fetch 실패: {e}", flush=True)
        return None

    def _db_upsert_token(self, token: Dict[str, Any]) -> bool:
        if not (self.store_mode == "db" and self.master_key and self.token_profile):
            print("[DB] upsert 건너뜀: MCP_URL/API_KEY/TOKEN_PROFILE 확인 필요", flush=True)
            return False
        try:
            url = f"{self.mcp_url}/admin/tokens"
            body = {"profile": self.token_profile, "token": token, "tenant_id": self.tenant_id, "client_id": self.client_id, "scopes": " ".join(self.scopes)}
            r = requests.post(url, headers={"x-api-key": self.master_key}, json=body, timeout=10)
            if r.status_code not in (200, 201):
                print(f"[DB] token upsert 실패: {r.status_code} {r.text[:200]}", flush=True)
                return False
            return True
        except Exception as e:
            print(f"[DB] token upsert 오류: {e}", flush=True)
            return False

    def _db_verify_meta_saved(self) -> bool:
        try:
            url = f"{self.mcp_url}/admin/tokens/by-profile/{self.token_profile}"
            r = requests.get(url, headers={"x-api-key": self.master_key}, timeout=10)
            if r.status_code != 200:
                return False
            data = r.json() or {}
            return bool(data.get("client_id") == self.client_id and data.get("tenant_id") == self.tenant_id)
        except Exception:
            return False

    # 파일 스토리지 제거

    # UV(디바이스 코드) 흐름 삭제로 _get_app 및 디바이스 인증 사용 안함

    # ---------------------------
    # 토큰 저장/로드/검증
    # ---------------------------
    def save_token(self, token: Dict[str, Any]):
        # DB에 토큰 반영
        token_only = {k: v for k, v in token.items() if k in self.TOKEN_KEYS}
        # expires_on/expires_in 정규화
        if "expires_in" in token_only and "expires_on" not in token_only:
            try:
                token_only["expires_on"] = int(time.time()) + int(token_only.get("expires_in", 0))
            except Exception:
                pass
        self._db_upsert_token(token_only)

    def load_token(self) -> Optional[Dict[str, Any]]:
        """
        DB에서 토큰 필드만 반환(없으면 None).
        """
        t = self._db_get_token()
        if t and t.get("access_token"):
            return t
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
    # UV(디바이스 코드) 인증 흐름 제거

    def authenticate(self) -> bool:
        """
        기존 토큰 검증 → refresh_token 갱신 (디바이스 코드 플로우 없음)
        """
        print("--- 인증 자동화 시작 ---", flush=True)
        token = self.load_token()
        if token:
            print("[세션 감지] 기존 토큰 존재(DB)", flush=True)
            if self.is_token_valid(token):
                print("[세션 유효] 실제 Azure API 검증까지 통과, 바로 사용 가능", flush=True)
                return True
            print("[세션 만료/유효하지 않음] 갱신 필요", flush=True)
        else:
            print("[세션 없음] 최초 인증 필요", flush=True)
        # refresh_token 갱신 시도
        ok = self.refresh_if_needed(slack_seconds=0)
        if ok:
            print("[세션 갱신] refresh_token 기반 갱신 성공", flush=True)
            return True
        print("[인증 실패] 유효한 refresh_token이 없어 갱신할 수 없습니다.", flush=True)
        print("힌트: 관리자/운영자가 발급한 토큰을 DB 프로필로 import 하세요.", flush=True)
        return False

    # ---------------------------
    # 갱신(Refresh Token)
    # ---------------------------
    def _refresh_with_refresh_token(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        OAuth2 v2.0 refresh_token 그랜트로 토큰 갱신.
        Public client에서는 client_secret 없이 가능.
        """
        rt = token.get("refresh_token")
        if not rt:
            print("[갱신 불가] refresh_token 없음", flush=True)
            return None
        tenant = self.tenant_id or "organizations"
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "scope": " ".join(self.scopes) or "Tasks.ReadWrite",
        }
        try:
            resp = requests.post(url, data=data, timeout=15)
            if resp.status_code != 200:
                print(f"[갱신 실패] {resp.status_code}: {resp.text[:200]}", flush=True)
                return None
            res = resp.json()
            # expires_on 계산 보정
            try:
                if "expires_in" in res and "expires_on" not in res:
                    res["expires_on"] = int(time.time()) + int(res.get("expires_in", 0))
            except Exception:
                pass
            return res
        except Exception as e:
            print(f"[갱신 오류] {e}", flush=True)
            return None

    def refresh_if_needed(self, slack_seconds: int = 600) -> bool:
        """
        만료 전 slack_seconds 이하로 남았거나 만료된 경우 refresh_token으로 갱신.
        디바이스 코드(uv) 폴백은 제거됨.
        """
        token = self.load_token() or {}
        now = int(time.time())
        try:
            exp = int(token.get("expires_on", 0))
        except Exception:
            exp = 0

        if token.get("access_token") and exp and (exp - now) > slack_seconds:
            print("[갱신 불필요] 만료까지 여유 있음", flush=True)
            return True

        print("[갱신 시도] refresh_token 기반", flush=True)
        new_tok = self._refresh_with_refresh_token(token)
        if new_tok and "access_token" in new_tok:
            self.save_token(new_tok)
            print("[갱신 성공] refresh_token 사용", flush=True)
            return True

        # UV(디바이스 코드) 폴백 제거
        print("[갱신 실패] refresh_token 갱신 불가", flush=True)
        return False

    def auto_refresh(self, interval_seconds: int = 60, slack_seconds: int = 600):
        """
        주기적으로 DB 토큰 상태를 점검하여 만료 전에 자동 갱신.
        컨테이너에서 포그라운드 서비스로 실행 권장.
        """
        print(f"[auto-refresh] interval={interval_seconds}s slack={slack_seconds}s", flush=True)
        while True:
            try:
                ok = self.refresh_if_needed(slack_seconds=slack_seconds)
                print(f"[auto-refresh] tick: {'ok' if ok else 'fail'}", flush=True)
            except Exception as e:
                print(f"[auto-refresh] 오류: {e}", flush=True)
            time.sleep(max(10, int(interval_seconds)))

    # ---------------------------
    # --- register_app: Microsoft Graph API 기반 (Azure CLI 제거) ---
    def _admin_access_token(self, interactive: bool = False) -> str:
        tenant = os.environ.get("ADMIN_TENANT_ID") or self.tenant_id
        cid = os.environ.get("ADMIN_CLIENT_ID")
        secret = os.environ.get("ADMIN_CLIENT_SECRET")
        # 1) 앱 권한(client credentials) 우선
        if tenant and cid and secret and not interactive:
            token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
            data = {
                "client_id": cid,
                "client_secret": secret,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default",
            }
            resp = requests.post(token_url, data=data, timeout=15)
            if resp.status_code != 200:
                raise RuntimeError(f"관리자 토큰 발급 실패: {resp.status_code} {resp.text[:200]}")
            return resp.json().get("access_token", "")
        # 2) Fallback: Delegated(관리자) 로그인
        print("[Fallback] 관리자 앱 권한 미제공. Microsoft 계정으로 직접 로그인합니다.", flush=True)
        try:
            import webbrowser
            import uuid
        except ImportError:
            print("webbrowser, uuid 모듈 필요", flush=True)
            raise
        device_code_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Microsoft 공식 public client
        scope = "https://graph.microsoft.com/.default offline_access"
        # 1단계: 디바이스 코드 요청
        resp = requests.post(device_code_url, data={"client_id": client_id, "scope": scope}, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"Device code 요청 실패: {resp.status_code} {resp.text[:200]}")
        dc = resp.json()
        print(f"[로그인 안내] {dc['message']}", flush=True)
        try:
            webbrowser.open(dc["verification_uri"])
        except Exception:
            pass
        # 2단계: 폴링
        interval = int(dc.get("interval", 5))
        expires = int(dc.get("expires_in", 900))
        start = time.time()
        while True:
            if time.time() - start > expires:
                raise RuntimeError("디바이스 코드 만료")
            time.sleep(interval)
            poll = requests.post(token_url, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": dc["device_code"],
            }, timeout=10)
            if poll.status_code == 200:
                tok = poll.json()
                print("[로그인 성공]", flush=True)
                return tok["access_token"]
            elif poll.status_code in (400, 401):
                err = poll.json().get("error", "")
                if err in ("authorization_pending", "slow_down"):
                    continue
                raise RuntimeError(f"로그인 실패: {poll.text}")
            else:
                raise RuntimeError(f"로그인 실패: {poll.status_code} {poll.text}")

    def _graph(self, method: str, path: str, *, token: str, json_body: Optional[dict] = None, params: Optional[dict] = None) -> dict:
        url = f"https://graph.microsoft.com/v1.0{path}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        func = requests.get if method.upper() == "GET" else requests.post if method.upper() == "POST" else requests.patch
        r = func(url, headers=headers, json=json_body, params=params, timeout=20)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Graph {method} {path} 실패: {r.status_code} {r.text[:200]}")
        return r.json()

    def register_app(self, interactive: bool = False):
        """
        Microsoft Graph API로 퍼블릭 클라이언트 앱 등록/재사용.
        우선순위:
          1) 환경/스토어의 CLIENT_ID가 있으면 조회 후 재사용
          2) displayName prefix 검색으로 최신 앱 재사용
          3) 없으면 신규 생성 (isFallbackPublicClient, requiredResourceAccess 포함)
        필요 권한: Application.ReadWrite.All (client credentials)
        """
        import time

        admin_token = self._admin_access_token(interactive=interactive)
        # interactive 모드 안내
        if interactive:
            print("[INFO] --interactive 모드: 관리자 계정 직접 로그인 후 앱 등록 진행", flush=True)
        prefix = self._get('APP_PREFIX', 'mcp-todo-server')
        desired_scopes = "Tasks.ReadWrite"

        graph_app_id = "00000003-0000-0000-c000-000000000000"  # Microsoft Graph
        tasks_readwrite_scope = "2219042f-cab5-40cc-b0d2-16b1540b4c5f"  # Delegated Scope

        # 0) CLIENT_ID 지정 시 검증 후 재사용
        pre_client = (os.environ.get("CLIENT_ID") or self.client_id or "").strip()
        if pre_client:
            data = self._graph("GET", "/applications", token=admin_token, params={"$filter": f"appId eq '{pre_client}'"})
            if isinstance(data.get("value"), list) and data["value"]:
                tenant_id = os.environ.get("ADMIN_TENANT_ID") or self.tenant_id
                self.client_id = pre_client
                self.tenant_id = tenant_id
                self.scopes = self._normalize_scopes(desired_scopes)
                # 메타만 DB에 반영 + 검증
                ok = self._db_upsert_token({})
                if ok and self._db_verify_meta_saved():
                    print(f"[DB] 메타 저장 완료(profile={self.token_profile})", flush=True)
                else:
                    print("[경고] DB 메타 저장 확인 실패: MCP_URL/API_KEY/TOKEN_PROFILE/권한 확인", flush=True)
                print(f"[재사용] 기존 앱 CLIENT_ID={pre_client}", flush=True)
                return pre_client, tenant_id, desired_scopes
            else:
                print(f"[무시] CLIENT_ID={pre_client} 미존재 → 탐색/생성 진행", flush=True)

        # 1) prefix 검색 (최신 1개)
        cand_id = None
        try:
            q = {"$filter": f"startsWith(displayName,'{prefix}')", "$orderby": "createdDateTime desc", "$top": 1}
            res = self._graph("GET", "/applications", token=admin_token, params=q)
            items = res.get("value", []) if isinstance(res, dict) else []
            if items:
                cand_id = items[0].get("appId")
        except Exception as e:
            print(f"[참고] 기존 앱 탐색 실패: {e}", flush=True)

        if cand_id:
            tenant_id = os.environ.get("ADMIN_TENANT_ID") or self.tenant_id
            self.client_id = cand_id
            self.tenant_id = tenant_id
            self.scopes = self._normalize_scopes(desired_scopes)
            ok2 = self._db_upsert_token({})
            if ok2 and self._db_verify_meta_saved():
                print(f"[DB] 메타 저장 완료(profile={self.token_profile})", flush=True)
            else:
                print("[경고] DB 메타 저장 확인 실패: MCP_URL/API_KEY/TOKEN_PROFILE/권한 확인", flush=True)
            print(f"[재사용 확정] CLIENT_ID={cand_id}", flush=True)
            return cand_id, tenant_id, desired_scopes

        # 2) 신규 생성
        app_name = f"{prefix}-{int(time.time())}"
        body = {
            "displayName": app_name,
            "isFallbackPublicClient": True,
            "requiredResourceAccess": [
                {
                    "resourceAppId": graph_app_id,
                    "resourceAccess": [
                        {"id": tasks_readwrite_scope, "type": "Scope"}
                    ],
                }
            ],
        }
        created = self._graph("POST", "/applications", token=admin_token, json_body=body)
        client_id = created.get("appId")
        tenant_id = os.environ.get("ADMIN_TENANT_ID") or self.tenant_id
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.scopes = self._normalize_scopes(desired_scopes)
        ok3 = self._db_upsert_token({})
        if ok3 and self._db_verify_meta_saved():
            print(f"[DB] 메타 저장 완료(profile={self.token_profile})", flush=True)
        else:
            print("[경고] DB 메타 저장 확인 실패: MCP_URL/API_KEY/TOKEN_PROFILE/권한 확인", flush=True)
        print(f"CLIENT_ID={client_id}", flush=True)
        print(f"TENANT_ID={tenant_id}", flush=True)
        print(f"SCOPES={desired_scopes}", flush=True)
        print("[완료] (Graph) 앱 등록/메타 저장 완료", flush=True)
        return client_id, tenant_id, desired_scopes
    

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
        print("[안내] DB 기반 토큰은 서버 측에서 관리됩니다. 필요 시 /admin/tokens API로 삭제를 수행하세요.", flush=True)

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
        self._db_upsert_token({})
        self._app = None
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

        p_register = sub.add_parser("register-app")
        p_register.add_argument("--interactive", action="store_true", help="관리자 client secret 없이 대화형(디바이스 코드)으로 앱 등록")

        p_refresh = sub.add_parser("refresh")
        p_refresh.add_argument("--slack-seconds", type=int, default=int(os.environ.get("REFRESH_SLACK", "600")))

        p_auto = sub.add_parser("auto-refresh")
        p_auto.add_argument("--interval-seconds", type=int, default=int(os.environ.get("REFRESH_INTERVAL", "60")))
        p_auto.add_argument("--slack-seconds", type=int, default=int(os.environ.get("REFRESH_SLACK", "600")))

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
            interactive = getattr(args, "interactive", False)
            self.register_app(interactive=interactive)
        elif cmd == "refresh":
            ok = self.refresh_if_needed(slack_seconds=getattr(args, "slack_seconds", 600))
            sys.exit(0 if ok else 1)
        elif cmd == "auto-refresh":
            self.auto_refresh(
                interval_seconds=getattr(args, "interval_seconds", 60),
                slack_seconds=getattr(args, "slack_seconds", 600),
            )
        elif cmd == "set-tenant":
            self.set_tenant(getattr(args, "tenant", None))
        else:
            parser.print_help()
            
            
            



def main():
    parser = argparse.ArgumentParser(description="AuthHelper CLI (no env)")
    parser.add_argument("--mcp-url", required=True, help="MCP 서버 URL (ex: http://localhost:8081)")
    parser.add_argument("--master-key", required=True, help="서버 관리자 API 키")
    parser.add_argument("--token-profile", default="default", help="토큰/메타 저장 프로필명")
    parser.add_argument("--tenant-id", default="organizations", help="Azure 테넌트 ID")
    parser.add_argument("--client-id", default="", help="앱 client_id (선택)")
    parser.add_argument("--scopes", default="Tasks.ReadWrite", help="OAuth2 scopes (공백구분)")
    # 나머지 명령/옵션은 기존 run_cmd에서 처리
    args, rest = parser.parse_known_args()
    helper = AuthHelper(
        mcp_url=args.mcp_url,
        master_key=args.master_key,
        token_profile=args.token_profile,
        tenant_id=args.tenant_id,
        client_id=args.client_id,
        scopes=args.scopes,
    )
    helper.run_cmd(rest)


if __name__ == "__main__":
    main()
