#!/usr/bin/env python3
"""Gate: at most one libs/* package in the working change."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import hook_response_mode, parse_mode  # noqa: E402
from _repo import changed_files, emit, packages_in_paths, read_stdin_json  # noqa: E402


def evaluate(*, base: str | None = None) -> tuple[bool, str]:
    packages = packages_in_paths(changed_files(base=base))
    if len(packages) <= 1:
        return True, f"one-package ok: {packages or ['(no libs package changes)']}"
    msg = (
        "Contribute shape violation: more than one package in the change: "
        + ", ".join(packages)
        + ". Keep the change to a single libs package."
    )
    return False, msg


def main() -> int:
    cli, argv = parse_mode()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    payload = {} if cli else read_stdin_json()
    ok, message = evaluate(base=args.base)
    if cli:
        if not ok:
            print(message, file=sys.stderr)
            return 1
        print(message)
        return 0

    event = hook_response_mode(payload)
    if event == "stop":
        emit({} if ok else {"followup_message": message})
        return 0
    if event == "preToolUse":
        if ok:
            emit({"permission": "allow"})
        else:
            emit(
                {
                    "permission": "deny",
                    "agent_message": message,
                    "user_message": message,
                }
            )
        return 0
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
