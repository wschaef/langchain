#!/usr/bin/env python3
"""Fail-path and happy-path checks for contribute hook scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / ".cursor" / "hooks"


def run(script: str, *, args: list[str] | None = None, stdin: str | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(HOOKS / script), *(args or [])]
    result = subprocess.run(
        cmd,
        cwd=REPO,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, ((result.stdout or "") + (result.stderr or "")).strip()


def main() -> int:
    failures: list[str] = []

    # Happy: uv allowed
    code, out = run("block_disallowed_shell.py", args=["--cli", "uv sync --all-groups"])
    if code != 0:
        failures.append(f"shell allow uv: {out}")

    # Fail: pip blocked
    code, out = run("block_disallowed_shell.py", args=["--cli", "pip install requests"])
    if code == 0:
        failures.append("shell should block pip")

    # Fail: force-push blocked
    code, out = run(
        "block_disallowed_shell.py", args=["--cli", "git push --force origin master"]
    )
    if code == 0:
        failures.append("shell should block force-push")

    # Hook JSON deny for poetry
    payload = json.dumps(
        {
            "hook_event_name": "beforeShellExecution",
            "command": "poetry add foo",
        }
    )
    code, out = run("block_disallowed_shell.py", stdin=payload)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        failures.append(f"shell hook JSON invalid: {out}")
    else:
        if data.get("permission") != "deny":
            failures.append(f"shell hook should deny poetry: {data}")

    # Package helpers via one-package on clean tree
    code, out = run("check_one_package.py", args=["--cli"])
    if code != 0:
        failures.append(f"one-package clean: {out}")

    # Drive-by deps: simulate preToolUse write to uv.lock
    payload = json.dumps(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Write",
            "tool_input": {"path": str(REPO / "libs/core/uv.lock")},
        }
    )
    code, out = run("check_no_driveby_deps.py", stdin=payload)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        failures.append(f"deps hook JSON invalid: {out}")
    else:
        if data.get("permission") != "deny":
            failures.append(f"deps hook should deny uv.lock write: {data}")

    # Package bound: declare core, attempt partners write
    state_dir = REPO / ".cursor" / "contribute"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    previous = state_path.read_text(encoding="utf-8") if state_path.exists() else None
    try:
        state_path.write_text(
            json.dumps(
                {
                    "issue": "#0",
                    "package": "libs/core",
                    "approved": True,
                    "assigned": True,
                    "confirmed": True,
                    "allow_deps": False,
                }
            ),
            encoding="utf-8",
        )
        payload = json.dumps(
            {
                "hook_event_name": "preToolUse",
                "tool_name": "Write",
                "tool_input": {
                    "path": str(REPO / "libs/partners/openai/langchain_openai/x.py")
                },
            }
        )
        code, out = run("check_package_bound.py", stdin=payload)
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            failures.append(f"bound hook JSON invalid: {out}")
        else:
            if data.get("permission") != "deny":
                failures.append(f"bound hook should deny other package: {data}")

        # Allow write inside declared package
        payload = json.dumps(
            {
                "hook_event_name": "preToolUse",
                "tool_name": "Write",
                "tool_input": {
                    "path": str(REPO / "libs/core/langchain_core/utils/x.py")
                },
            }
        )
        code, out = run("check_package_bound.py", stdin=payload)
        data = json.loads(out)
        if data.get("permission") != "allow":
            failures.append(f"bound hook should allow same package: {data}")
    finally:
        if previous is None:
            if state_path.exists():
                state_path.unlink()
        else:
            state_path.write_text(previous, encoding="utf-8")

    # Network heuristic: temp unit test file content check via helper
    sys.path.insert(0, str(HOOKS))
    from _repo import NETWORK_PATTERNS  # noqa: E402

    sample = "import requests\n\ndef test_x():\n    requests.get('https://example.com')\n"
    if not any(p.search(sample) for p in NETWORK_PATTERNS):
        failures.append("network patterns missed requests.get")

    if failures:
        print("SELFTEST FAILURES:")
        for item in failures:
            print("-", item)
        return 1
    print("selftest_hooks: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
