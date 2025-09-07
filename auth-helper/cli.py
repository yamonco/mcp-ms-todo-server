from __future__ import annotations
import sys
import time
import argparse
from .config import Settings
from . import tokens
from . import appreg


def cmd_init(cfg: Settings) -> int:
    print("--- Auth init ---")
    tok = tokens.load_token(cfg)
    if tok and tokens.is_token_valid(tok.get("access_token", "")):
        print("[OK] Token valid via Graph /me")
        return 0
    print("[INFO] No/expired token; trying refresh")
    if tokens.refresh_if_needed(cfg, slack_seconds=0):
        return 0
    print("[FAIL] No valid refresh_token. Import a valid token JSON into DB.")
    return 1


def cmd_status(cfg: Settings) -> int:
    tok = tokens.load_token(cfg)
    if not tok:
        print("No token.")
        return 0
    exp = tok.get("expires_on")
    try:
        exp_h = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(exp))) if exp else "unknown"
    except Exception:
        exp_h = "unknown"
    print(f"Token present. Local expiry: {exp_h}")
    return 0


def cmd_refresh(cfg: Settings, slack: int) -> int:
    ok = tokens.refresh_if_needed(cfg, slack_seconds=slack)
    return 0 if ok else 1


def cmd_auto_refresh(cfg: Settings, interval: int, slack: int) -> int:
    print(f"[auto-refresh] interval={interval}s slack={slack}s")
    while True:
        try:
            ok = tokens.refresh_if_needed(cfg, slack_seconds=slack)
            print(f"[auto-refresh] tick: {'ok' if ok else 'fail'}")
        except Exception as e:
            print(f"[auto-refresh] Error: {e}")
        time.sleep(max(10, int(interval)))


def cmd_set_tenant(cfg: Settings, new_tenant: str | None) -> int:
    if not new_tenant:
        new_tenant = input("Enter TENANT_ID (e.g., organizations|consumers|common or GUID): ").strip()
    if not new_tenant:
        print("TENANT_ID is invalid.")
        return 1
    cfg.tenant_id = new_tenant
    from . import dbsync
    dbsync.upsert_token(cfg, {})
    print(f"TENANT_ID set to '{new_tenant}'")
    return 0


def cmd_register_app(cfg: Settings, *, interactive: bool) -> int:
    appreg.register_app(cfg, interactive=interactive)
    return 0


def main(argv: list[str] | None = None) -> int:
    cfg = Settings.load()
    p = argparse.ArgumentParser(description="AuthHelper CLI (modular)")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("logout")  # no-op: DB 보관 안내만
    pr = sub.add_parser("register-app")
    pr.add_argument("--interactive", action="store_true", help="관리자 client secret 없이 대화형(디바이스 코드)으로 앱 등록")

    pref = sub.add_parser("refresh")
    pref.add_argument("--slack-seconds", type=int, default=cfg.refresh_slack)

    paut = sub.add_parser("auto-refresh")
    paut.add_argument("--interval-seconds", type=int, default=cfg.refresh_interval)
    paut.add_argument("--slack-seconds", type=int, default=cfg.refresh_slack)

    pset = sub.add_parser("set-tenant")
    pset.add_argument("--tenant", required=False)

    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    cmd = args.cmd or "init"

    if cmd == "init":
        return cmd_init(cfg)
    if cmd == "status":
        return cmd_status(cfg)
    if cmd == "logout":
        print("[안내] DB 기반 토큰은 서버 측에서 관리됩니다. 필요 시 /admin/tokens API로 삭제를 수행하세요.")
        return 0
    if cmd == "register-app":
        return cmd_register_app(cfg, interactive=getattr(args, "interactive", False))
    if cmd == "refresh":
        return cmd_refresh(cfg, slack=getattr(args, "slack_seconds", cfg.refresh_slack))
    if cmd == "auto-refresh":
        return cmd_auto_refresh(cfg, interval=getattr(args, "interval_seconds", cfg.refresh_interval), slack=getattr(args, "slack_seconds", cfg.refresh_slack))
    if cmd == "set-tenant":
        return cmd_set_tenant(cfg, getattr(args, "tenant", None))

    p.print_usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
