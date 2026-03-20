# sector-feeds AGENTS

Read the root policy chain first:

- `/Users/cjarguello/BitPod-App/taylored-policy.md`
- `/Users/cjarguello/BitPod-App/bitpod-docs/process/taylored-rule-registry.md`

This file adds repo-specific rules only.

Repo rule:

- this file adds instructions only
- it does not suspend root prohibitions unless it declares an explicit allowed exception
- any exception to a root prohibition must cite exact rule IDs and include scope,
  reason, conditions, owner role, and duration

## Rule Exceptions

- none

## Repo Focus

- use this repo for transcript ingestion, transformation, validation, and
  operator-facing content outputs
- use repo docs and README for domain context, but prefer this file for
  execution guidance
- keep stable pointers and permalink-facing files intact when the repo contract
  requires them

## Agent Routing

- `Engineer` / implementation agents: ingestion, parsing, storage, and output
  contract work
- `Explorer` / analysis agents: runbook lookup, contract tracing, and drift
  analysis
- `QA` / review agents: transcript quality checks, metadata quality, summary
  quality, and operator-facing output review

## Model Defaults

- prefer a lightweight/cost-efficient model for bulk transcript preparation and
  mechanical transformation work
- prefer a stronger frontier reasoning model for QA, review, metadata
  enrichment, and operator-facing summary quality
- treat these as repo defaults, not immutable global requirements

## Canonical Pointers

- README for repo purpose and navigation
- `docs/runbooks/` for run-specific contract details
- `docs/prompts/` only when a runbook explicitly points there

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
