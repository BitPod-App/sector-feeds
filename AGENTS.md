# sector-feeds AGENTS

Read the umbrella agent entrypoint first from the active workspace root:

- `$WORKSPACE/AGENTS.md`

For any new-file, retained-artifact, temporary-handoff, local-working-file, or
retrospective decision, follow:

- `$WORKSPACE/bitpod-docs/process/file-creation-and-artifact-placement-policy.md`

For Linear issue updates:

- treat `update Linear` as `make the issue materially more truthful`
- preserve existing Linear assignee/delegate by default; do not assign/delegate issues to Codex or mention `@Codex` unless the user explicitly wants a Codex cloud task from Linear
- use `$WORKSPACE/bitpod-tools/linear/docs/process/linear_operating_guide_v3.md` for the canonical detailed rule

This file adds repo-specific rules only.

## Health Check

Run from repo root:

```bash
bash scripts/check_taylor_skill.sh
bash scripts/check_taylor_agent.sh
```

Behavior:
- If Taylor prerequisites are missing in local workspace context, these scripts return `SKIP` with an explicit reason (exit 0).
- Set `BITPOD_TAYLOR_PREREQ_STRICT=1` to force hard-fail behavior.

## Review Bundle Gate

- No bundle = no review claim.
- Any claim of "line-by-line review" must include:
  - bundle file path
  - exact command used to generate it
- Standard command:

```bash
bash scripts/make_review_bundle.sh
```

## Review Bundle Format (strict)

Every review bundle must use this section order exactly:
- A) Context: repo, base branch, head branch, commit hashes, timestamp
- B) `git diff --stat` (`base...HEAD`)
- C) full `git diff` (`base...HEAD`)
- D) verification outputs (health checks/tests/scripts)
- E) decisions needed (explicit blockers/questions)

## Bridge Session Memory Capture (required)

When ending a Bridge GPT planning/review session, memory summary must be structured as:
- Decisions (locked)
- Invariants (locked)
- Next Actions (who/what)
- Risks / Unknowns
