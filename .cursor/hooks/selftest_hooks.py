#!/usr/bin/env python3
"""Fail-path and happy-path checks for contribute hook scripts.

Covers: disallowed shell, drive-by deps, package bound, multi-package,
missing tests, and unit-test network heuristic — not happy path only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    # Isolate from contribute session env left by prior runs.
    os.environ.pop("CONTRIBUTE_PACKAGE", None)
    os.environ.pop("CONTRIBUTE_DIFF_BASE", None)

    # --- disallowed shell ---
    code, out = run("block_disallowed_shell.py", args=["--cli", "uv sync --all-groups"])
    if code != 0:
        failures.append(f"shell allow uv: {out}")

    code, out = run("block_disallowed_shell.py", args=["--cli", "pip install requests"])
    if code == 0:
        failures.append("shell should block pip")

    code, out = run(
        "block_disallowed_shell.py", args=["--cli", "git push --force origin master"]
    )
    if code == 0:
        failures.append("shell should block force-push")

    code, out = run("block_disallowed_shell.py", args=["--cli", "conda install numpy"])
    if code == 0:
        failures.append("shell should block conda")

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

    # --- one-package clean ---
    code, out = run("check_one_package.py", args=["--cli"])
    if code != 0:
        failures.append(f"one-package clean: {out}")

    # --- drive-by deps (preToolUse) ---
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

    payload = json.dumps(
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Write",
            "tool_input": {"path": str(REPO / "libs/core/pyproject.toml")},
        }
    )
    code, out = run("check_no_driveby_deps.py", stdin=payload)
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        failures.append(f"deps pyproject JSON invalid: {out}")
    else:
        if data.get("permission") != "deny":
            failures.append(f"deps hook should deny pyproject.toml write: {data}")

    # --- package bound ---
    state_dir = REPO / ".cursor" / "contribute"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    previous = state_path.read_text(encoding="utf-8") if state_path.exists() else None
    scratch: list[Path] = []
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

        # Deny editing pack organs during a libs contribute
        payload = json.dumps(
            {
                "hook_event_name": "preToolUse",
                "tool_name": "Write",
                "tool_input": {"path": str(REPO / ".cursor/hooks/selftest_hooks.py")},
            }
        )
        code, out = run("check_no_cursor_pack_edits.py", stdin=payload)
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            failures.append(f"cursor-pack hook JSON invalid: {out}")
        else:
            if data.get("permission") != "deny":
                failures.append(f"cursor-pack should deny pack Write: {data}")

        # Allow session state under .cursor/contribute/
        payload = json.dumps(
            {
                "hook_event_name": "preToolUse",
                "tool_name": "Write",
                "tool_input": {"path": str(REPO / ".cursor/contribute/plan.md")},
            }
        )
        code, out = run("check_no_cursor_pack_edits.py", stdin=payload)
        data = json.loads(out)
        if data.get("permission") != "allow":
            failures.append(f"cursor-pack should allow contribute state: {data}")

        # --- multi-package fail (untracked scratch files) ---
        core_src = REPO / "libs/core/langchain_core/_selftest_pack_scratch.py"
        ts_src = (
            REPO
            / "libs/text-splitters/langchain_text_splitters/_selftest_pack_scratch.py"
        )
        _write(core_src, "# selftest scratch — delete me\n")
        _write(ts_src, "# selftest scratch — delete me\n")
        scratch.extend([core_src, ts_src])
        code, out = run("check_one_package.py", args=["--cli"])
        if code == 0:
            failures.append(f"one-package should fail on multi-package: {out}")

        # --- missing tests fail (source only in one package) ---
        ts_src.unlink(missing_ok=True)
        scratch = [core_src]
        code, out = run("check_tests_present.py", args=["--cli"])
        if code == 0:
            failures.append(f"tests-present should fail without tests: {out}")

        # --- network-in-unit fail ---
        unit_bad = (
            REPO
            / "libs/core/tests/unit_tests/_selftest_pack_network.py"
        )
        _write(
            unit_bad,
            "import requests\n\n"
            "def test_selftest_network() -> None:\n"
            "    requests.get('https://example.com')\n",
        )
        scratch.append(unit_bad)
        # also keep a source change so gates still see the package
        code, out = run("check_unit_no_network.py", args=["--cli"])
        if code == 0:
            failures.append(f"unit-no-network should fail on requests.get: {out}")

        # with a unit test present, tests-present should pass for core
        code, out = run("check_tests_present.py", args=["--cli"])
        if code != 0:
            failures.append(f"tests-present should pass with unit test: {out}")

        # helper-level multi-package path mapping
        sys.path.insert(0, str(HOOKS))
        from _repo import NETWORK_PATTERNS, packages_in_paths  # noqa: E402

        pkgs = packages_in_paths(
            [
                "libs/core/langchain_core/x.py",
                "libs/text-splitters/langchain_text_splitters/y.py",
            ]
        )
        if pkgs != ["libs/core", "libs/text-splitters"]:
            failures.append(f"packages_in_paths multi: {pkgs}")

        sample = "import requests\n\ndef test_x():\n    requests.get('https://example.com')\n"
        if not any(p.search(sample) for p in NETWORK_PATTERNS):
            failures.append("network patterns missed requests.get")
    finally:
        for path in scratch:
            path.unlink(missing_ok=True)
        if previous is None:
            if state_path.exists():
                state_path.unlink()
        else:
            state_path.write_text(previous, encoding="utf-8")

    if failures:
        print("SELFTEST FAILURES:")
        for item in failures:
            print("-", item)
        return 1
    print("selftest_hooks: all checks passed (happy + fail paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
