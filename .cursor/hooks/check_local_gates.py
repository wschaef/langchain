#!/usr/bin/env python3
"""Run format / lint / test for a touched package (verifier / CI-complement).

Not wired as an always-on session hook — invoke from the verifier agent or CLI.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo import REPO_ROOT, changed_files, declared_package, packages_in_paths  # noqa: E402


def package_dir(package: str) -> Path:
    return REPO_ROOT / package


def run_make(package: str, target: str) -> tuple[bool, str]:
    cwd = package_dir(package)
    if not cwd.is_dir():
        return False, f"package directory missing: {package}"
    makefile = cwd / "Makefile"
    if not makefile.is_file():
        return False, f"no Makefile in {package}"
    env = os.environ.copy()
    env.setdefault("UV_FROZEN", "true")
    result = subprocess.run(
        ["make", target],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    log = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        return False, f"make {target} failed in {package}\n{log[-4000:]}"
    return True, f"make {target} ok in {package}"


def resolve_package(explicit: str | None, base: str | None) -> str | None:
    if explicit:
        return explicit.rstrip("/")
    declared = declared_package()
    if declared:
        return declared
    packages = packages_in_paths(changed_files(base=base))
    if len(packages) == 1:
        return packages[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument(
        "--targets",
        default="format,lint,test",
        help="Comma-separated make targets (default: format,lint,test)",
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip make test (useful for quick shape checks)",
    )
    args = parser.parse_args()
    package = resolve_package(args.package, args.base)
    if not package:
        print(
            "check_local_gates: could not resolve a single package "
            "(pass --package or set contribute state)",
            file=sys.stderr,
        )
        return 2
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    if args.skip_test:
        targets = [t for t in targets if t != "test"]
    failures: list[str] = []
    for target in targets:
        ok, message = run_make(package, target)
        print(message)
        if not ok:
            failures.append(target)
    if failures:
        print(f"local gates failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print(f"local gates passed for {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
