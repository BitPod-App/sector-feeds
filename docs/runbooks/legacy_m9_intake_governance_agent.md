# Legacy M-9 Intake Governance Agent (Historical Reference)

Status: legacy reference only

## Objective

Preserve the first `M-9` intake-governance concept as historical
reference while keeping the old policy-as-code assumptions visible.

## Independent Agent Scope

- repo focus: `sector-feeds`
- writes:
  - `milestones/legacy_m9_intake_policy.json`
  - `artifacts/coordination/intake_gate_daily_status.json`
  - `artifacts/coordination/intake_gate_daily_drift_report.json`
  - `artifacts/coordination/intake_gate_daily_drift_report.md`
  - `artifacts/coordination/m9_tracker.md` (or configured milestone tracker path)
- reads:
  - producer artifact from `bitregime-core`
  - legacy M-5 artifacts for historical continuity

## Boundaries

- historical reference only; do not treat this runbook as active default
  canon
- do not modify producer contract logic in `bitregime-core` unless explicitly requested
- do not push directly to `main`
- preserve history pointers when operational truth changes:
  - `milestones/m5_policy.json`
  - `artifacts/coordination/intake_gate_daily_status.json`
  - `artifacts/coordination/intake_gate_daily_drift_report.md`
  - `docs/runbooks/intake_gate_retrospective_learnings.md`
  - retrospective PR pointer: `https://github.com/cjarguello/bitpod/pull/8`

## Acceptance Criteria

Machine-readable:
- status JSON validates against `validate_status_contract`
- `milestone_close_ready` exists and is boolean
- milestone-specific key exists (example: `m9_close_ready_3_consecutive_greens`)
- drift JSON check set is complete and `drift_ok` is explicit

Human-readable:
- drift markdown generated with expected vs observed checks
- milestone tracker generated with normalized entry
- runbook instructions remain reproducible with one-command daily run

## Failure Classes

- `contract_validation_failure`
- `status_contract_failure`
- `policy_drift_failure`
- `observability_degradation`
- `artifact_integrity_failure`

## Escalation Thresholds

- immediate escalation on invalid policy JSON or unsupported validation target
- guardrail escalation at `2` consecutive failures
- freeze action: `freeze_intake_contract_changes_and_route_to_incident_triage`

## Rollback Path

1. freeze intake contract changes.
2. run v1 rollback diagnostic output.
3. revert latest legacy M-9 governance commit(s) on branch if
   status/drift contracts regress.
4. restore last-known-good policy target and rerun daily gate.

## Legacy Implementation Slice (M9-S1)

- add `milestones/legacy_m9_intake_policy.json`
- emit milestone-agnostic close-ready keys while preserving legacy M-5 key
- support milestone tracker output path via env var

## Validation Commands

From `/Users/cjarguello/bitpod-app/sector-feeds`:

```bash
python3 -m unittest tests/test_intake_gate_policy.py

BITPOD_INTAKE_POLICY_JSON=milestones/legacy_m9_intake_policy.json \
BITPOD_INTAKE_DAILY_MILESTONE_TRACKER_MD=artifacts/coordination/m9_tracker.md \
bash scripts/run_intake_gate_daily.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc

cat artifacts/coordination/intake_gate_daily_status.json
cat artifacts/coordination/intake_gate_daily_drift_report.md
cat artifacts/coordination/m9_tracker.md
```
