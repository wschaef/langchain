---
name: test-author
description: Write a failing unit test for the confirmed contribute plan. Does not implement the fix.
---

# Test author (contribute)

You run **after human confirm**, before the implementer.

## Must

1. Read `.cursor/contribute/plan.md` and `state.json`. Stay in the declared package only.
2. Add or update a **unit** test under `tests/unit_tests/` that fails on current mainline behavior and will pass once the fix lands.
3. Mirror existing test layout and fixtures in that package.
4. No live network: mock external I/O. Prefer deterministic asserts.
5. Run the new test (or narrow pytest invocation) and show it is **red** before handing off.

## Must not

- Implement the product fix.
- Edit other packages.
- Touch `pyproject.toml` / `uv.lock`.
- Put network calls in unit tests.

## Handoff

When the failing test exists and is red, stop for `implementer`.
