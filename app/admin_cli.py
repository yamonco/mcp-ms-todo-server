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
    return hdrs


def cmd_policy_reload(args: argparse.Namespace) -> int:
    import httpx
    url = _mcp_base_url().rstrip('/') + "/ops/policy/reload"
    with httpx.Client(timeout=10) as c:
        r = c.post(url, headers=_auth_headers())
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="admin-cli", description="Admin helpers (ops)")
    sub = p.add_subparsers(dest="cmd")
    sp_pr = sub.add_parser("policy-reload", help="Reload Casbin enforcer via /ops")
    sp_pr.set_defaults(func=cmd_policy_reload)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
