---
name: pr-brief
description: Open or update the contribute PR using the structured brief template. No more code changes.
---

# PR brief (contribute)

You open or update the pull request after verifier pass.

## Must

1. Read the plan, issue ref, and verification notes.
2. Use simple English. No slang.
3. Align with `.github/PULL_REQUEST_TEMPLATE.md` and fill this brief (P7):

```text
Fixes #<n>

<1-2 sentence user story: who benefits, what broke, how this fixes it>

## Release note
<user-visible change, or "n/a — chore/docs/test-only">

## How verified
<commands / tests run; expected red then green>

## For PM
<user/impact + release-note one-liner>

## For QA
<what to retest; unit vs anything deferred>

## For DevOps
<package touched; lockfile/deps unchanged?; CI surface>

## Deferred / path to production
<what remains after merge — release workflow note OK>
```

4. Title: Conventional Commits with scope (`fix(core): …`, etc.).
5. Create or update a **draft** PR unless the human asked otherwise.
6. Stage **only** product/test files under the declared package. Never add `.cursor/` pack organs to the product commit.
7. Note AI-agent involvement briefly.

## Must not

- Change product or test code.
- Force-push.
- Expand scope.

## Done

Return the PR URL and a short status to the parent skill.
