# plan.md

## Goal
Ship one low-blast, real engineering slice that proves the full M-9 agent workflow with auditable artifacts.

## Problem statement (2-5 lines)
The proving-run process currently depends on manual copy commands to create run artifacts. That adds inconsistency and creates avoidable setup drift. We need a deterministic initializer script so Taylor can dispatch, engineers can execute predictably, and Vera can verify the same output shape every run.

## Scope
In:
- Add `scripts/init_proving_run.sh` to scaffold `docs/agents/runs/<RUN_ID>/` with all required templates.
- Add runbook usage snippet in `docs/agents/proving-run/M9_AGENT_OS_PROVING_RUN_v1.md`.
- Verify script idempotency and path creation behavior.

Out:
- Any Linear schema changes.
- Changes to Vera verdict contract semantics.
- Automation scheduling or CI workflow changes.

## Acceptance criteria (3-7)
- [x] Running `bash scripts/init_proving_run.sh M9-PROVING-RUN-001` creates all six required run files under `docs/agents/runs/M9-PROVING-RUN-001/`.
- [x] Re-running the command does not corrupt existing files (idempotent behavior is documented and verified).
- [x] Script exits non-zero with clear usage text when `RUN_ID` is missing.
- [x] Runbook includes exact command and expected output paths.
- [x] `execution_notes.md` captures command evidence and resulting file list.

## Dependencies
- Existing template files in `docs/agents/proving-run/templates/`.
- Engineer write access to `bitpod` repo.

## Risks + mitigations
- Risk: script overwrites existing run artifacts unexpectedly.
  - Mitigation: default to no-overwrite behavior and print per-file status.
- Risk: path typos create partial scaffolds.
  - Mitigation: strict `set -euo pipefail`, preflight path checks, and explicit final summary.

## Dispatch
- Linear issue: `TBD` (Linear track intentionally deferred during proving run bootstrap)
- Engineer owner: Atlas (default)
- Vera QA trigger condition: script + runbook doc changes are committed and command evidence is attached.
- CJ gate required: yes
