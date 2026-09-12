# Contribute pack (project `.cursor/`)

Human-initiated `/contribute <issue-ref>` path for one-package LangChain contributions.

| Organ | Role |
| --- | --- |
| `commands/contribute.md` | Entry |
| `skills/contribute/` | Orchestrator + `run_package_gates.py` |
| `agents/` | planner → test-author → implementer → verifier → pr-brief |
| `hooks/` + `hooks.json` | Session gates (shell, package bound, deps; stop follow-ups for shape/tests) |
| `rules/contribute-shape.mdc` | Thin always-on nudge for `libs/**` |

Local format/lint/test: verifier via `check_local_gates.py` / `run_package_gates.py` — not every edit hook.

Cloud boot files `environment.json` and `install.sh` stay as-is.

See learn-cursor `technical-interview/implementation-plan.md` for design intent.
