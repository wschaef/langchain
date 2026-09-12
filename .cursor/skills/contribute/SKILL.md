---
name: contribute
description: Human-initiated LangChain contribution path — grill, plan, confirm, then test-author → implementer → verifier → pr-brief. Use when the user runs /contribute or asks to contribute against an issue.
---

# Contribute

Orchestrate a one-package contribution on this LangChain fork.

## Preconditions

1. **Issue reference required.** If the user did not pass an issue/bug/feature ref, stop and ask for one. Do not invent a ticket.
2. **Soft approval / assignment stop.** Inspect the issue. If it is not approved by a maintainer and/or not assigned (per LangChain external-contribution norms), stop and tell the human what is missing. Do not continue to implementation.
   - Prefer a GitHub issue on this fork. If the fork has issues disabled, an upstream `langchain-ai/langchain` issue URL/number is an acceptable reference; still require explicit human confirm (or operator-authorized pack validation) before setting `approved` / `assigned` in `.cursor/contribute/state.json`.
   - Optional proxy: set those flags in `state.json` only after confirm — never invent approval.
3. Keep existing Cloud boot files untouched: `.cursor/environment.json`, `.cursor/install.sh`.
4. Use `.mcp.json` for docs/API only. Do not add MCP servers.
5. Do not duplicate `AGENTS.md` into always-on context; reference it when needed.

## Flow

```text
/contribute <issue-ref>
  → grill (this skill / parent)
  → agents/planner          # readonly plan; write plan.md + state.json
  → [human confirms]
  → agents/test-author
  → agents/implementer
  → agents/verifier
  → agents/pr-brief
```

### 1. Grill (human present)

Ask short clarifying questions until acceptance is clear:

- What is broken or missing?
- How to reproduce (if a bug)?
- Done when?
- Any API compatibility constraints?

Derive answers from the issue body when the human is unavailable only if an explicit operator instruction allows autonomous pack validation — otherwise wait.

### 2. Planner

Delegate to the `planner` subagent. It must emit the P6 plan template into `.cursor/contribute/plan.md` and refresh `state.json` (`confirmed: false`).

### 3. Confirm gate

Show the plan. Wait for explicit human **go** / adjust. Do not start `test-author` until confirm.

On confirm, set `confirmed: true` in `.cursor/contribute/state.json`.

### 4. Autonomous execute

Run in order (no further interviews):

1. `test-author` — failing unit test first
2. `implementer` — minimal fix
3. `verifier` — `python3 .cursor/skills/contribute/scripts/run_package_gates.py --package <pkg>`
4. `pr-brief` — draft PR with P7 brief

## Shape rules (enforced by hooks/scripts)

- One package only
- No drive-by `pyproject.toml` / `uv.lock`
- Stay inside declared package
- Unit tests with source; no live network in unit tests
- Block `pip` / `poetry` / `conda` and force-push
- Format / lint / test: verifier (not every session edit hook)

## State files

- `.cursor/contribute/state.json` — issue, package, flags (`approved`, `assigned`, `confirmed`, `allow_deps`)
- `.cursor/contribute/plan.md` — confirmed plan text

These paths are gitignored except `.gitignore`.

## Out of scope

Hunter intake, dual-mode product switches, self-improving pack loops, new MCP servers.
