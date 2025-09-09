from __future__ import annotations
import argparse
import os
import json


def _mcp_base_url() -> str:
    return os.getenv("MCP_URL", f"http://localhost:{os.getenv('PORT','8081')}")


def _auth_headers() -> dict:
    bt = (
        os.getenv("AUTHENTIK_TOKEN")
        or os.getenv("OIDC_TOKEN")
        or os.getenv("BEARER_TOKEN")
        or os.getenv("ACCESS_TOKEN")
    )
    hdrs = {"content-type": "application/json"}
    if bt:
        hdrs["authorization"] = f"Bearer {bt}"
    ak = os.getenv("ADMIN_API_KEY") or os.getenv("API_KEY")
    if ak:
        hdrs["x-api-key"] = ak
    return hdrs


def cmd_policy_reload(args: argparse.Namespace) -> int:
    import httpx
    url = _mcp_base_url().rstrip('/') + "/ops/policy/reload"
    with httpx.Client(timeout=10) as c:
        r = c.post(url, headers=_auth_headers())
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False))
    return 0


def cmd_apps_register_or_reuse(args: argparse.Namespace) -> int:
    import httpx
    url = _mcp_base_url().rstrip('/') + "/admin/apps/register_or_reuse"
    payload = {"app_prefix": args.app_prefix, "display_name": args.display_name}
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers=_auth_headers(), json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False))
    return 0


def cmd_tokens_upsert(args: argparse.Namespace) -> int:
    import sys
    import httpx
    url = _mcp_base_url().rstrip('/') + "/admin/tokens"
    payload = {
        "profile": args.profile,
        "tenant_id": args.tenant_id,
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "scope": args.scope,
        "token_endpoint": args.token_endpoint,
        "app_id": args.app_id,
    }
    if args.from_stdin:
        try:
            raw = json.loads(sys.stdin.read() or "{}")
            payload.update({
                "access_token": raw.get("access_token"),
                "refresh_token": raw.get("refresh_token"),
                "expires_at": raw.get("expires_at"),
            })
        except Exception:
            pass
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers=_auth_headers(), json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False))
    return 0


def cmd_apikeys_add(args: argparse.Namespace) -> int:
    import httpx
    url = _mcp_base_url().rstrip('/') + "/admin/api-keys"
    payload = {
        "user_id": args.user_id,
        "name": args.name,
        "role": args.role,
        "groups": args.groups,
        "token_profile": args.token_profile,
        "token_id": args.token_id,
        "app_id": args.app_id,
    }
    with httpx.Client(timeout=15) as c:
        r = c.post(url, headers=_auth_headers(), json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="admin-cli", description="Admin helpers (ops, apps, tokens, api-keys)")
    sub = p.add_subparsers(dest="cmd")
    sp_pr = sub.add_parser("policy-reload", help="Reload Casbin enforcer via /ops")
    sp_pr.set_defaults(func=cmd_policy_reload)

    sp_app = sub.add_parser("apps-register-or-reuse", help="Register or reuse app by prefix (DB record only)")
    sp_app.add_argument("--app-prefix", required=True)
    sp_app.add_argument("--display-name", default=None)
    sp_app.set_defaults(func=cmd_apps_register_or_reuse)

    sp_tok = sub.add_parser("tokens-upsert", help="Upsert token profile (read token from stdin if provided)")
    sp_tok.add_argument("--profile", required=True)
    sp_tok.add_argument("--tenant-id")
    sp_tok.add_argument("--client-id")
    sp_tok.add_argument("--client-secret")
    sp_tok.add_argument("--scope")
    sp_tok.add_argument("--token-endpoint")
    sp_tok.add_argument("--app-id", type=int)
    sp_tok.add_argument("--from-stdin", action="store_true")
    sp_tok.set_defaults(func=cmd_tokens_upsert)

    sp_key = sub.add_parser("apikeys-add", help="Create API key for a user")
    sp_key.add_argument("--user-id", required=False)
    sp_key.add_argument("--name", required=False)
    sp_key.add_argument("--role", required=False)
    sp_key.add_argument("--groups", nargs='*')
    sp_key.add_argument("--token-profile", required=False)
    sp_key.add_argument("--token-id", type=int)
    sp_key.add_argument("--app-id", type=int)
    sp_key.set_defaults(func=cmd_apikeys_add)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
