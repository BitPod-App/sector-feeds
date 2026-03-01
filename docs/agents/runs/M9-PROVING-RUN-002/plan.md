# plan.md

## Goal
Ship a low-blast script hardening change that proves the M9 workflow on a real tracked issue.

## Problem statement (2-5 lines)
`scripts/init_proving_run.sh` validates template presence during each copy call. If a template is missing, failure occurs mid-flow and does not provide a clear preflight summary of all missing templates. We need deterministic preflight validation before scaffolding starts.

## Scope
In:
- Add required-template preflight validation to `scripts/init_proving_run.sh`.
- Fail fast with concise missing-template list before run directory scaffold/copy.
- Preserve current behavior for missing args, idempotent reruns, and fresh scaffolds.

Out:
- Changes to artifact template contents or Vera contract semantics.
- Linear schema/automation updates.
- CI workflow changes.

## Acceptance criteria (3-7)
- [x] Missing template set fails with explicit summary and non-zero exit.
- [x] Failure happens before run directory is created for missing-template path.
- [x] Existing run id still emits six `SKIP existing` entries and success footer.
- [x] Fresh run id still creates six required files and success footer.
- [x] Missing arg path still exits `2` with usage output.

## Dependencies
- Existing proving-run template files under `docs/agents/proving-run/templates/`.
- GitHub issue tracking: `#17`.

## Risks + mitigations
- Risk: preflight check changes error semantics unexpectedly.
  - Mitigation: preserve exit codes and validate all prior paths.
- Risk: temporary template rename during test could leave workspace inconsistent.
  - Mitigation: restore template immediately in same verification command.

## Dispatch
- Tracking issue: `https://github.com/cjarguello/bitpod/issues/17`
- Linear issue: `TBD` (to be mirrored by Taylor during Linear sync)
- Engineer owner: Atlas (executed in this run)
- Vera QA trigger condition: script diff + command evidence captured in `execution_notes.md`
- CJ gate required: yes
