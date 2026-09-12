#!/usr/bin/env python3
"""Gate: product contribute runs must not edit the `.cursor/` pack.

Session state under `.cursor/contribute/` is allowed (gitignored). Pack organs
(hooks, agents, skills, …) belong on the pack PR, not on product PRs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import hook_response_mode, parse_mode  # noqa: E402
from _repo import (  # noqa: E402
    changed_files,
    declared_package,
    emit,
    read_stdin_json,
    repo_relative,
)


def is_pack_path(path: str) -> bool:
    """Return True for committed pack paths (not session state)."""
    normalized = path.replace("\\", "/")
    if not normalized.startswith(".cursor/"):
        return False
    if normalized.startswith(".cursor/contribute/"):
        return False
    return True


def evaluate_paths(paths: list[str], *, target: str | None) -> tuple[bool, str]:
    """Fail when a libs package contribute touches pack files."""
    if not target or not target.startswith("libs/"):
        return True, "cursor-pack ok: no libs package declared"
    offenders = [p for p in paths if is_pack_path(p)]
    if not offenders:
        return True, "cursor-pack ok: no pack file edits"
    msg = (
        "Contribute shape violation: product run must not edit `.cursor/` pack "
        "files (use the pack PR for that). Offenders: "
        + ", ".join(offenders[:12])
    )
    return False, msg


def paths_from_payload(payload: dict) -> list[str]:
    event = hook_response_mode(payload)
    if event in ("afterFileEdit", "preToolUse"):
        file_path = payload.get("file_path") or ""
        tool_input = payload.get("tool_input")
        if not file_path and isinstance(tool_input, dict):
            file_path = tool_input.get("path") or tool_input.get("file_path") or ""
        return [repo_relative(str(file_path))] if file_path else []
    return changed_files(include_untracked=False)


def main() -> int:
    cli, argv = parse_mode()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    payload = {} if cli else read_stdin_json()
    target = declared_package()
    paths = (
        changed_files(base=args.base, include_untracked=False)
        if cli
        else paths_from_payload(payload)
    )
    ok, message = evaluate_paths(paths, target=target)

    if cli:
        if not ok:
            print(message, file=sys.stderr)
            return 1
        print(message)
        return 0

    event = hook_response_mode(payload)
    if event == "preToolUse":
        if ok or not paths:
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
    if event == "stop":
        emit({} if ok else {"followup_message": message})
        return 0
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
