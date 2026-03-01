# Intake Gate Retrospective Learnings

Use this file for lightweight archived learnings tied to daily intake gate drift.

## Entry Template

- date_utc: `<YYYY-MM-DD>`
- milestone: `M-5`
- owner_context: `<single_engineer_mode | owner>`
- signal: `<what drift/incident was detected>`
- expected_policy: `<policy key/value from milestones/m5_policy.json>`
- observed_run_metadata: `<status key/value from intake_gate_daily_status.json>`
- root_cause: `<brief cause>`
- action_taken: `<what changed>`
- validation_proof:
  - drift_report: `artifacts/coordination/intake_gate_daily_drift_report.md`
  - status_json: `artifacts/coordination/intake_gate_daily_status.json`
  - tests: `<commands>`
- follow_up: `<optional>`

## Notes

- Keep entries concise and evidence-first.
- Do not duplicate full logs; link to generated daily artifacts.
- For now (single engineer), `owner_context` should be `single_engineer_mode`. Add explicit owner only when team rotation exists.
