#!/usr/bin/env python3
"""Gate: edits stay inside the declared contribute package."""

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
    is_ignored_path,
    package_for_path,
    read_stdin_json,
    repo_relative,
)


def evaluate_paths(paths: list[str], *, target: str | None) -> tuple[bool, str]:
    if not target:
        return True, "package-bound skipped: no declared CONTRIBUTE_PACKAGE / state"
    offenders: list[str] = []
    for path in paths:
        if is_ignored_path(path):
            continue
        pkg = package_for_path(path)
        if pkg is None:
            continue
        if pkg != target:
            offenders.append(path)
    if not offenders:
        return True, f"package-bound ok: {target}"
    msg = (
        f"Contribute shape violation: files outside declared package {target}: "
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
    return changed_files()


def main() -> int:
    cli, argv = parse_mode()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    payload = {} if cli else read_stdin_json()
    target = declared_package()
    paths = changed_files(base=args.base) if cli else paths_from_payload(payload)
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
