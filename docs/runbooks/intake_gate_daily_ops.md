# Intake Gate Daily Ops (v2 Default)

This runbook covers intake gate operations hardening now that `bitregime_core_intake.v2` is default end-to-end.

## Scope

- daily automated v2-default handshake gate on `main`
- retained daily pass/fail history with classified failure reasons
- one-command operator triage + rollback diagnostic path
- consecutive-failure alert/escalation guardrail

## One-Command Operator Triage

From `/Users/cjarguello/bitpod-app/bitpod`:

```bash
bash scripts/run_intake_gate_triage.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc
```

Outputs:

- `artifacts/coordination/intake_gate_daily_status.json` (machine-readable)
- `artifacts/coordination/intake_gate_daily_summary.md` (human-readable)
- `artifacts/coordination/intake_gate_daily_drift_report.json` (machine-readable drift checks)
- `artifacts/coordination/intake_gate_daily_drift_report.md` (human-readable drift checks)
- `artifacts/coordination/m5_tracker.md` (legacy-compatible milestone tracker default path)
- `artifacts/coordination/intake_gate_triage.md` (operator playbook snapshot)
- `artifacts/coordination/intake_gate_daily_log.jsonl` (retained daily history)

Healthy marker:

- `contract_ok: true`
- `status_contract_ok: true`
- `drift_ok: true`

Policy file (source of truth):

- `milestones/m5_policy.json`
- includes `required_validation_target`, guardrail threshold, close-ready threshold, and freeze action
- `owner_oncall` is optional and intended for future multi-engineer windows

## Exact Commands

Reproduce:

```bash
bash scripts/run_intake_gate_daily.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc
```

Verify:

```bash
cat artifacts/coordination/intake_gate_daily_status.json
cat artifacts/coordination/intake_gate_daily_summary.md
cat artifacts/coordination/intake_gate_daily_drift_report.md
cat artifacts/coordination/m5_tracker.md
```

Rollback diagnostic (last known-good behavior path):

```bash
BITPOD_INTAKE_VALIDATION_TARGET=bitregime_core_intake.v1 \
bash scripts/check_bitregime_core_intake_handshake.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc \
  artifacts/coordination/intake_gate_daily_v1_rollback_diagnostic.json
```

## Failure Classification

Daily status includes explicit root-cause category tags derived from contract errors:

- `missing_file`
- `unsupported_contract_version`
- `invalid_json`
- `missing_field`
- `field_validation_error`
- `duplicate_field_value`
- `invalid_episode_row`
- `unsupported_validation_target`
- `unknown_validation_error`

## Alert Threshold And Escalation

Rollback guardrail:

- threshold: `2` consecutive RED daily runs
- trigger field: `rollback_guardrail_triggered: true`
- required escalation: `freeze_intake_contract_changes_and_route_to_incident_triage`

Policy:

- If 2 consecutive daily failures occur, freeze new intake contract changes and route to incident triage before further rollout work.

## M-5 Exit Criterion

- Require at least `3` consecutive daily GREEN runs.
- Daily status fields:
  - `milestone_close_ready` (milestone-agnostic)
  - milestone-specific key (example: `m9_close_ready_3_consecutive_greens`)
  - `m5_close_ready_3_consecutive_greens` (legacy compatibility)

## Archived Learnings

- Keep drift findings in a separate retrospective file:
  - `docs/runbooks/intake_gate_retrospective_learnings.md`
