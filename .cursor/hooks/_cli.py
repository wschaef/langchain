"""CLI vs hook mode helpers."""

from __future__ import annotations

import sys
from typing import Any


def parse_mode(argv: list[str] | None = None) -> tuple[bool, list[str]]:
    """Return (cli_mode, argv_without_cli_flag)."""
    args = list(sys.argv[1:] if argv is None else argv)
    cli = False
    if "--cli" in args:
        cli = True
        args = [a for a in args if a != "--cli"]
    elif sys.stdin.isatty():
        cli = True
    return cli, args


def hook_response_mode(payload: dict[str, Any]) -> str:
    """Return hook event name or empty."""
    event = payload.get("hook_event_name")
    return event if isinstance(event, str) else ""
