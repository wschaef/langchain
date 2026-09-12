# /contribute

Human-initiated entry for a LangChain contribution.

## Usage

```text
/contribute <issue-ref>
```

Examples: `/contribute #40360`, `/contribute https://github.com/wschaef/langchain/issues/1`

## Behavior

1. Require an issue / bug / feature **reference**. If missing, stop and ask for one.
2. Run the `contribute` skill end-to-end:
   - Soft stop if the issue is not approved / assigned (per project process).
   - Grill for acceptance criteria, then delegate `planner`.
   - Wait for explicit human confirm before autonomous execution.
   - After confirm: `test-author` → `implementer` → `verifier` → `pr-brief`.
3. Do not pick a different issue. Do not touch packages outside the plan.
4. Use existing project docs (`AGENTS.md`, contributing guide) and `.mcp.json` docs/API only — do not invent new MCP servers.
