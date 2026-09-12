#!/usr/bin/env python3
"""Gate: block drive-by pyproject.toml / uv.lock edits unless allowed."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import hook_response_mode, parse_mode  # noqa: E402
from _repo import changed_files, emit, load_state, read_stdin_json, repo_relative  # noqa: E402

DEP_FILES = ("pyproject.toml", "uv.lock")


def is_dep_file(path: str) -> bool:
    return Path(path).name in DEP_FILES


def deps_allowed() -> bool:
    return bool(load_state().get("allow_deps"))


def evaluate_paths(paths: list[str]) -> tuple[bool, str]:
    if deps_allowed():
        return True, "drive-by deps ok: allow_deps set in contribute state"
    offenders = [p for p in paths if is_dep_file(p)]
    if not offenders:
        return True, "drive-by deps ok: no pyproject.toml / uv.lock changes"
    msg = (
        "Contribute shape violation: dependency files changed without allow_deps: "
        + ", ".join(offenders)
        + ". Do not edit pyproject.toml or uv.lock unless a maintainer approved it."
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
    paths = changed_files(base=args.base) if cli else paths_from_payload(payload)
    ok, message = evaluate_paths(paths)

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
