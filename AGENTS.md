# Taylor Skill Pointer (Repo-Portable)

This repository points to the external canonical Taylor skill at:

- `~/.agents/skills/taylor/SKILL.md`

Do not duplicate or override Taylor's canonical behavior/spec in this repo.

## Taylor Skill Folder Status

- Keep `~/.agents/skills/taylor` as the canonical Taylor spec + references (required).
- Current Taylor runtime code lives outside this repo in `bitpod-taylor-runtime`; `sector-feeds` should not depend on Taylor for steady-state feed execution.
- Repo docs are pointer + optional health-check surfaces only; do not duplicate spec text.

### Deprecation Criteria (future, not current)

Only consider deprecating the external skill folder after all are true:
- a stable `taylor` CLI or equivalent runtime contract is available and documented.
- Determinism tests + manifests are in place.
- Canonical contract docs are mirrored in-repo without split-brain.
- A single source of truth is explicitly selected (external or in-repo), never both.

## Canonical Reference Anchors

- `~/.agents/skills/taylor/references/taylor-agent-contract.md`
- `~/.agents/skills/taylor/references/report-template.md` (periodic + ad hoc)
- `~/.agents/skills/taylor/references/bridge-gpt-team-sessions.md`

## Health Check

Run from repo root:

```bash
bash scripts/check_taylor_skill.sh
```

Optional, only when a real `taylor` CLI is installed or `TAYLOR_BIN` is set:

```bash
bash scripts/check_taylor_agent.sh
```

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

## Taylor Runtime Commands

If a `taylor` CLI is installed and intended for use:

- `taylor whoami`
- `taylor self-test`
- `taylor ask "<question>" [--context <path>]`
- `taylor chat`

Do not assume a repo-local `tools/taylor` path in this repository.

## QA Modes

- LOCAL (offline, enforced): deterministic local QA artifacts; merge gate for critical surfaces.
- BRIDGE (optional, stronger proof): GPT-backed independent QA evidence path; historical docs may still refer to Taylor-era QA naming.
- CHAT (human workflow): planning and interpretation, not a merge gate.

## Merge Policy

- Default merge gate: LOCAL QA artifacts are required for critical surface changes.
- BRIDGE QA is additive evidence when available, but not required for merge.
- Missing LOCAL QA artifacts on critical surfaces must fail closed.

## Context Preservation FYI (ExtensionGPT + Taylor)

For future historical continuity, include concise context pointers in PR/commit text when intake gate policy/drift behavior changes:
- policy path: `milestones/m5_policy.json`
- daily status artifact: `artifacts/coordination/intake_gate_daily_status.json`
- daily drift report: `artifacts/coordination/intake_gate_daily_drift_report.md`
- retrospective learnings: `docs/runbooks/intake_gate_retrospective_learnings.md`

This is an FYI context pattern, not a merge gate.
