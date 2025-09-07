#!/usr/bin/env python3
"""
Simple CLI to manage users and call MCP endpoints.
Usage examples:
  Python runs (venv):
    echo '{"access_token":"...","refresh_token":"..."}' | python -m app.cli profiles import --profile alice --from-stdin
    python -m app.cli users list
    python -m app.cli users delete --key <API_KEY>
Environment:
  MCP_URL (default: http://localhost:${PORT or 8081})
  API_KEY  (master key for admin)
"""
import os
import sys
import json
import argparse
import httpx
import time


def _base_url() -> str:
    url = os.getenv("MCP_URL")
    if url:
        return url.rstrip("/")
    port = os.getenv("PORT", "8081")
    return f"http://localhost:{port}"


def _master_headers() -> dict:
    key = os.getenv("API_KEY")
    if not key:
        # fallback: read from .env in cwd
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("API_KEY="):
                        key = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass
    if not key:
        print("API_KEY not found. Set env or add API_KEY=... in .env", file=sys.stderr)
        sys.exit(2)
    return {"x-api-key": key, "content-type": "application/json"}


def cmd_users_add(args: argparse.Namespace) -> None:
    url = _base_url() + "/admin/users"
    payload = {
        "template": args.template,
        "allowed_tools": args.allowed_tools,
        "note": args.note,
        "user_id": args.user_id,
        "name": args.name,
        "token_profile": args.token_profile,
        "token_id": args.token_id,
    }
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers=_master_headers(), json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def cmd_users_list(args: argparse.Namespace) -> None:
    url = _base_url() + "/admin/users"
    with httpx.Client(timeout=20) as c:
        r = c.get(url, headers=_master_headers())
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def cmd_users_update(args: argparse.Namespace) -> None:
    url = _base_url() + f"/admin/api-keys/{args.key}"
    payload = {
        "template": args.template,
        "allowed_tools": args.allowed_tools,
        "note": args.note,
        "user_id": args.user_id,
        "name": args.name,
        "token_profile": args.token_profile,
        "token_id": args.token_id,
    }
    # Drop None values to keep patch minimal
    payload = {k: v for k, v in payload.items() if v is not None}
    with httpx.Client(timeout=20) as c:
        r = c.patch(url, headers=_master_headers(), json=payload)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def cmd_users_delete(args: argparse.Namespace) -> None:
    url = _base_url() + f"/admin/api-keys/{args.key}"
    with httpx.Client(timeout=20) as c:
        r = c.delete(url, headers=_master_headers())
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def _env_default(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)


def _copy_file(src: str, dst: str) -> None:
    _ensure_dir(dst)
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        f.write(data)


def cmd_users_onboard(args: argparse.Namespace) -> None:
    # Ensure server is up (wait up to 45s)
    _wait_for_server(timeout=45.0)
    template = args.template or _env_default("USER_TEMPLATE_DEFAULT", "lite")
    name = args.name
    user_id = args.user_id
    token_profile = args.token_profile or user_id

    if template == "custom" and not args.allowed_tools:
        raise SystemExit("custom template requires --allowed-tools")

    # If token_id provided, attach directly; else require raw token JSON via arg or stdin
    token_id = args.token_id
    if token_id is None:
        raw = args.token
        if args.from_stdin:
            raw = sys.stdin.read()
        if not raw:
            raise SystemExit("Provide --token '<JSON>' or --from-stdin, or use --token-id")
        try:
            token = json.loads(raw)
        except Exception as e:
            raise SystemExit(f"Invalid --token JSON: {e}")
        url = _base_url() + "/admin/tokens"
        body = {"profile": token_profile, "token": token}
        with httpx.Client(timeout=20) as c:
            r = c.post(url, headers=_master_headers(), json=body)
            r.raise_for_status()
            up = r.json()
        token_id = up.get("id")
    payload = argparse.Namespace(
        template=template,
        allowed_tools=args.allowed_tools,
        note=args.note,
        user_id=user_id,
        name=name,
        token_profile=token_profile,
        token_id=token_id,
    )
    cmd_users_add(payload)
    

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mcp-cli", description="MCP Server CLI")
    sub = p.add_subparsers(dest="cmd")

    g_users = sub.add_parser("users", help="Manage users")
    sub_users = g_users.add_subparsers(dest="action")

    p_add = sub_users.add_parser("add", help="Add user and generate API key")
    p_add.add_argument("--user-id", required=True)
    p_add.add_argument("--name", required=False)
    p_add.add_argument("--template", required=True, choices=["lite", "default", "custom"])
    p_add.add_argument("--allowed-tools", nargs="*", default=None, help="Only for custom template")
    p_add.add_argument("--token-profile", required=False, help="DB token profile name")
    p_add.add_argument("--token-id", required=False, type=int, help="DB token id (preferred)")
    p_add.add_argument("--note", required=False)
    p_add.set_defaults(func=cmd_users_add)

    p_list = sub_users.add_parser("list", help="List users")
    p_list.set_defaults(func=cmd_users_list)

    p_del = sub_users.add_parser("delete", help="Delete by API key")
    p_del.add_argument("--key", required=True)
    p_del.set_defaults(func=cmd_users_delete)

    p_upd = sub_users.add_parser("update", help="Update user meta by API key")
    p_upd.add_argument("--key", required=True)
    p_upd.add_argument("--template", choices=["lite", "default", "custom"], required=False)
    p_upd.add_argument("--allowed-tools", nargs="*", default=None)
    p_upd.add_argument("--note", required=False)
    p_upd.add_argument("--user-id", required=False)
    p_upd.add_argument("--name", required=False)
    p_upd.add_argument("--token-profile", required=False)
    p_upd.add_argument("--token-id", required=False, type=int)
    p_upd.set_defaults(func=cmd_users_update)

    p_on = sub_users.add_parser("onboard", help="Import token JSON (arg/stdin) → add user")
    p_on.add_argument("--user-id", required=True)
    p_on.add_argument("--name", required=False)
    p_on.add_argument("--template", required=False, choices=["lite", "default", "custom"], help="Default from USER_TEMPLATE_DEFAULT or 'lite'")
    p_on.add_argument("--allowed-tools", nargs="*", default=None)
    p_on.add_argument("--token-profile", required=False, help="DB token profile name; default = user-id")
    p_on.add_argument("--token", required=False, help="Raw token JSON string (use --token-id to skip)")
    p_on.add_argument("--from-stdin", action="store_true", help="Read raw token JSON from stdin")
    p_on.add_argument("--token-id", required=False, type=int, help="DB token id to attach (skips import)")
    p_on.add_argument("--note", required=False)
    # Helper flow removed
    p_on.set_defaults(func=cmd_users_onboard)

    # profiles helper
    g_prof = sub.add_parser("profiles", help="Manage DB token profiles")
    sub_prof = g_prof.add_subparsers(dest="action")

    p_imp = sub_prof.add_parser("import", help="Import raw token JSON into a DB profile")
    p_imp.add_argument("--profile", required=True)
    p_imp.add_argument("--token", required=False, help="Raw token JSON string")
    p_imp.add_argument("--from-stdin", action="store_true", help="Read raw token JSON from stdin")
    p_imp.set_defaults(func=cmd_profiles_import)

    p_pl = sub_prof.add_parser("list", help="List profiles (DB)")
    p_pl.set_defaults(func=cmd_profiles_list)

    # auth helper (deprecated path; prefer profiles import)
    g_auth = sub.add_parser("auth", help="Auth helper wrapper (deprecated)")
    sub_auth = g_auth.add_subparsers(dest="action")

    p_login = sub_auth.add_parser("login-import", help="(deprecated) kept for compatibility; prefer 'profiles import'")
    p_login.add_argument("--profile", required=True, help="DB token profile name")
    p_login.add_argument("--token", required=False, help="Raw token JSON string")
    p_login.add_argument("--from-stdin", action="store_true", help="Read raw token JSON from stdin")
    p_login.set_defaults(func=cmd_auth_login_import)

    # RBAC roles
    g_roles = sub.add_parser("roles", help="Manage RBAC roles")
    sub_roles = g_roles.add_subparsers(dest="action")

    p_rl = sub_roles.add_parser("list", help="List roles")
    p_rl.set_defaults(func=cmd_roles_list)

    p_rp = sub_roles.add_parser("put", help="Create/Update a role")
    p_rp.add_argument("--name", required=True)
    p_rp.add_argument("--tools", nargs="+", required=True)
    p_rp.set_defaults(func=cmd_roles_put)

    p_rd = sub_roles.add_parser("delete", help="Delete a role")
    p_rd.add_argument("--name", required=True)
    p_rd.set_defaults(func=cmd_roles_delete)

    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    try:
        args.func(args)
        return 0
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"Missing dependency: {e}", file=sys.stderr)
        return 2


def _wait_for_server(timeout: float = 30.0, interval: float = 0.5) -> None:
    url = _base_url().rstrip("/") + "/health"
    headers = _master_headers()
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=3.0) as c:
                r = c.get(url, headers=headers)
                if r.status_code == 200:
                    return
                last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(interval)
    hint = "힌트: dev에서는 별도 터미널에서 'make dev-serve'로 서버를 먼저 띄워주세요. prod는 'make prod-up' 후 MCP_URL 지정."
    raise SystemExit(f"Server not ready at {url}: {last_err}. {hint}")

def cmd_profiles_import(args: argparse.Namespace) -> None:
    import json
    prof = args.profile
    raw = args.token
    if args.from_stdin:
        raw = sys.stdin.read()
    if not raw:
        raise SystemExit("Provide --token '<JSON>' or --from-stdin")
    try:
        token = json.loads(raw)
    except Exception as e:
        raise SystemExit(f"Invalid --token JSON: {e}")
    url = _base_url() + "/admin/tokens"
    body = {"profile": prof, "token": token}
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers=_master_headers(), json=body)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def cmd_profiles_list(args: argparse.Namespace) -> None:
    import json
    url = _base_url() + "/admin/tokens"
    with httpx.Client(timeout=20) as c:
        r = c.get(url, headers=_master_headers())
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


def _admin_get(path: str) -> dict:
    with httpx.Client(timeout=20) as c:
        r = c.get(_base_url() + path, headers=_master_headers())
        r.raise_for_status()
        return r.json()


def _admin_put(path: str, body: dict) -> dict:
    with httpx.Client(timeout=20) as c:
        r = c.put(_base_url() + path, headers=_master_headers(), json=body)
        r.raise_for_status()
        return r.json()


def _admin_delete(path: str) -> dict:
    with httpx.Client(timeout=20) as c:
        r = c.delete(_base_url() + path, headers=_master_headers())
        r.raise_for_status()
        return r.json()


def cmd_roles_list(args: argparse.Namespace) -> None:
    print(json.dumps(_admin_get("/admin/rbac/roles"), ensure_ascii=False, indent=2))


def cmd_roles_put(args: argparse.Namespace) -> None:
    body = {"tools": args.tools}
    print(json.dumps(_admin_put(f"/admin/rbac/roles/{args.name}", body), ensure_ascii=False, indent=2))


def cmd_roles_delete(args: argparse.Namespace) -> None:
    print(json.dumps(_admin_delete(f"/admin/rbac/roles/{args.name}"), ensure_ascii=False, indent=2))


def _run(cmd: list[str]) -> None:
    import subprocess
    subprocess.run(cmd, check=True)


def cmd_auth_login_import(args: argparse.Namespace) -> None:
    # Deprecated: simply upsert provided token JSON into DB profile
    import json
    prof = args.profile
    raw = args.token
    if args.from_stdin:
        raw = sys.stdin.read()
    if not raw:
        raise SystemExit("Provide --token '<JSON>' or --from-stdin")
    try:
        token = json.loads(raw)
    except Exception as e:
        raise SystemExit(f"Invalid --token JSON: {e}")
    url = _base_url() + "/admin/tokens"
    body = {"profile": prof, "token": token}
    with httpx.Client(timeout=20) as c:
        r = c.post(url, headers=_master_headers(), json=body)
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
