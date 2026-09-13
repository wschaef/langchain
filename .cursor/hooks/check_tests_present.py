#!/usr/bin/env python3
"""Gate: source changes under libs/<pkg>/ must include a tests path in the diff."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import hook_response_mode, parse_mode  # noqa: E402
from _repo import (  # noqa: E402
    changed_files,
    emit,
    is_source_path,
    is_unit_test_path,
    package_for_path,
    read_stdin_json,
)


def evaluate(*, base: str | None = None) -> tuple[bool, str]:
    paths = changed_files(base=base)
    source_pkgs = {package_for_path(p) for p in paths if is_source_path(p)}
    source_pkgs.discard(None)
    if not source_pkgs:
        return True, "tests-present ok: no package source changes"
    test_pkgs: set[str] = set()
    for path in paths:
        normalized = path.replace("\\", "/")
        if is_unit_test_path(path) or (
            "/tests/" in normalized and normalized.endswith(".py")
        ):
            pkg = package_for_path(path)
            if pkg:
                test_pkgs.add(pkg)
    missing = sorted(source_pkgs - test_pkgs)
    if not missing:
        return True, f"tests-present ok for {sorted(source_pkgs)}"
    msg = (
        "Contribute test gate: source changed without tests in the same package: "
        + ", ".join(missing)
        + ". Add unit tests under tests/unit_tests/ for the declared package."
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

    if hook_response_mode(payload) == "stop":
        emit({} if ok else {"followup_message": message})
        return 0
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
