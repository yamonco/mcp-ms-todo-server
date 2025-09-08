from __future__ import annotations
from .loader import load_helper_module


def main() -> int:
    cli = load_helper_module("cli")
    return int(cli.main())


if __name__ == "__main__":
    raise SystemExit(main())

