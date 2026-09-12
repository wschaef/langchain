#!/usr/bin/env python3
"""Run all contribute package gates for the verifier agent.

Shape / test scripts always run. Local format/lint/test run unless --shape-only.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[3] / "hooks"
REPO_ROOT = Path(__file__).resolve().parents[4]


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out = ((result.stdout or "") + (result.stderr or "")).strip()
    return result.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument(
        "--shape-only",
        action="store_true",
        help="Skip make format/lint/test (session-cheap mode)",
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="When running local gates, skip make test",
    )
    args = parser.parse_args()
    base_args = ["--base", args.base] if args.base else []

    checks: list[tuple[str, list[str]]] = [
        ("check_one_package.py", ["--cli", *base_args]),
        ("check_package_bound.py", ["--cli", *base_args]),
        ("check_no_driveby_deps.py", ["--cli", *base_args]),
        ("check_no_cursor_pack_edits.py", ["--cli", *base_args]),
        ("check_tests_present.py", ["--cli", *base_args]),
        ("check_unit_no_network.py", ["--cli", *base_args]),
    ]

    failures: list[str] = []
    for name, extra in checks:
        code, out = run([sys.executable, str(HOOKS / name), *extra])
        print(f"== {name} (exit {code}) ==")
        if out:
            print(out)
        if code != 0:
            failures.append(name)

    if not args.shape_only:
        local_extra: list[str] = list(base_args)
        if args.package:
            local_extra.extend(["--package", args.package])
        if args.skip_test:
            local_extra.append("--skip-test")
        code, out = run(
            [sys.executable, str(HOOKS / "check_local_gates.py"), *local_extra]
        )
        print(f"== check_local_gates.py (exit {code}) ==")
        if out:
            print(out)
        if code != 0:
            failures.append("check_local_gates.py")

    if failures:
        print("FAILED:", ", ".join(failures), file=sys.stderr)
        return 1
    print("All package gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
