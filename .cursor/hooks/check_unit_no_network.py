#!/usr/bin/env python3
"""Gate: heuristic ban on live network calls inside unit tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli import hook_response_mode, parse_mode  # noqa: E402
from _repo import changed_files, emit, read_stdin_json, unit_test_network_hits  # noqa: E402


def evaluate(*, base: str | None = None) -> tuple[bool, str]:
    hits = unit_test_network_hits(changed_files(base=base))
    if not hits:
        return True, "unit-no-network ok"
    msg = (
        "Contribute test gate: unit tests appear to use live network APIs: "
        + ", ".join(hits)
        + ". Mock external I/O in unit tests."
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
