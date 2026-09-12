"""Shared helpers for contribute pack check scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = REPO_ROOT / ".cursor" / "contribute" / "state.json"
LIBS_PREFIX = "libs/"

# Paths that are never counted as a product package change.
IGNORED_TOP_LEVEL = (
    ".cursor/",
    ".github/",
    "docs/",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    ".gitignore",
    ".mcp.json",
)


def read_stdin_json() -> dict[str, Any]:
    """Parse JSON from stdin; empty object when stdin is empty or invalid."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def emit(payload: dict[str, Any]) -> None:
    """Write a JSON hook response to stdout."""
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout text."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd or REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def changed_files(*, base: str | None = None) -> list[str]:
    """List changed files vs base (default merge-base with origin/master, else HEAD)."""
    if base is None:
        base = os.environ.get("CONTRIBUTE_DIFF_BASE")
    if base is None:
        merge_base = git("merge-base", "HEAD", "origin/master").strip()
        base = merge_base or "HEAD"
    tracked = git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    unstaged = git("diff", "--name-only", "--diff-filter=ACMR")
    staged = git("diff", "--name-only", "--cached", "--diff-filter=ACMR")
    untracked = git("ls-files", "--others", "--exclude-standard")
    files: set[str] = set()
    for blob in (tracked, unstaged, staged, untracked):
        for line in blob.splitlines():
            path = line.strip()
            if path:
                files.add(path.replace("\\", "/"))
    return sorted(files)


def is_ignored_path(path: str) -> bool:
    """Return True when path is outside package contribution gates."""
    normalized = path.replace("\\", "/")
    return any(normalized == p or normalized.startswith(p) for p in IGNORED_TOP_LEVEL)


def package_for_path(path: str) -> str | None:
    """Map a repo-relative path to a libs package key, or None."""
    normalized = path.replace("\\", "/")
    if is_ignored_path(normalized) or not normalized.startswith(LIBS_PREFIX):
        return None
    parts = normalized.split("/")
    if len(parts) < 2:
        return None
    if parts[1] == "partners":
        if len(parts) < 3:
            return None
        return f"libs/partners/{parts[2]}"
    return f"libs/{parts[1]}"


def packages_in_paths(paths: list[str]) -> list[str]:
    """Unique package keys touched by paths, sorted."""
    found: set[str] = set()
    for path in paths:
        pkg = package_for_path(path)
        if pkg:
            found.add(pkg)
    return sorted(found)


def load_state() -> dict[str, Any]:
    """Load contribute session state if present."""
    if not STATE_PATH.is_file():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def declared_package() -> str | None:
    """Return the declared target package from state or env."""
    env_pkg = os.environ.get("CONTRIBUTE_PACKAGE", "").strip()
    if env_pkg:
        return env_pkg.rstrip("/")
    state = load_state()
    pkg = state.get("package")
    if isinstance(pkg, str) and pkg.strip():
        return pkg.strip().rstrip("/")
    return None


def repo_relative(path: str) -> str:
    """Convert an absolute or relative path to a repo-relative POSIX path."""
    p = Path(path)
    if not p.is_absolute():
        return path.replace("\\", "/")
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.replace("\\", "/")


def is_unit_test_path(path: str) -> bool:
    """Heuristic: path looks like a unit test file under a package."""
    normalized = path.replace("\\", "/")
    return "/tests/unit_tests/" in normalized and normalized.endswith(".py")


def is_source_path(path: str) -> bool:
    """Heuristic: product source under a package (not tests)."""
    normalized = path.replace("\\", "/")
    if package_for_path(normalized) is None:
        return False
    if "/tests/" in normalized:
        return False
    return normalized.endswith(".py")


NETWORK_PATTERNS = (
    re.compile(r"\brequests\.(get|post|put|delete|request)\s*\("),
    re.compile(r"\bhttpx\.(get|post|put|delete|request|Client|AsyncClient)\s*\("),
    re.compile(r"\burllib\.request\."),
    re.compile(r"\bsocket\.create_connection\s*\("),
    re.compile(r"\baiohttp\."),
)


def unit_test_network_hits(paths: list[str]) -> list[str]:
    """Return unit-test paths that appear to make live network calls."""
    hits: list[str] = []
    for path in paths:
        if not is_unit_test_path(path):
            continue
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8")
        except OSError:
            continue
        for pattern in NETWORK_PATTERNS:
            if pattern.search(text):
                hits.append(path)
                break
    return hits
