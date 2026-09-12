#!/usr/bin/env python3
"""Gate: block disallowed shell patterns (pip/poetry/conda, force-push, etc.)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import parse_mode  # noqa: E402
from _repo import emit, read_stdin_json  # noqa: E402

RULES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(^|[;&|]\s*)(pip3?|pipx)\s+(install|uninstall|download)\b"),
        "Use uv, not pip/pipx, for environment and dependency operations.",
    ),
    (
        re.compile(r"(^|[;&|]\s*)poetry\s+"),
        "Use uv, not poetry, for environment and dependency operations.",
    ),
    (
        re.compile(r"(^|[;&|]\s*)conda\s+"),
        "Use uv, not conda, for environment and dependency operations.",
    ),
    (
        re.compile(r"git\s+push\b[^\n]*--force\b|git\s+push\b[^\n]*\s-f\b"),
        "Force-push is disallowed in the contribute path.",
    ),
    (
        re.compile(r"git\s+push\b[^\n]*--force-with-lease\b"),
        "Force-push is disallowed in the contribute path.",
    ),
]


def evaluate_command(command: str) -> tuple[bool, str]:
    text = command.strip()
    if not text:
        return True, "shell ok: empty"
    for pattern, reason in RULES:
        if pattern.search(text):
            return False, f"Disallowed shell command blocked: {reason} Command: {text}"
    return True, "shell ok"


def main() -> int:
    cli, argv = parse_mode()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="")
    args = parser.parse_args(argv)
    payload = {} if cli else read_stdin_json()
    command = args.command or str(payload.get("command") or "")
    tool_input = payload.get("tool_input")
    if not command and isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    ok, message = evaluate_command(command)

    if cli:
        if not ok:
            print(message, file=sys.stderr)
            return 1
        print(message)
        return 0

    if ok:
        emit({"permission": "allow", "continue": True})
    else:
        emit(
            {
                "permission": "deny",
                "continue": True,
                "user_message": message,
                "agent_message": message,
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
