# Legacy Tuesday Report Runbook

## Intent

Keep the original Tuesday personal-use readiness flow stable, predictable, and lowest-cost.

## Canonical ad hoc commands

```bash
# canonical legacy Tuesday readiness/status check
bash scripts/run_legacy_tuesday_track.sh jack_mallers_show

# or report-only
bash scripts/report_show_weekly_status.sh jack_mallers_show tuesday
```

## Canonical output

- `artifacts/jack_mallers_show_tuesday_report.md`
- Prompt: `docs/prompts/legacy_tuesday_single_prompt.md`

## Success criteria

- `run_status` is `ok`
- `included_in_pointer` is `True`
- `run_is_recent` is `True`
- `intake_ready` is `True`

## Notes

- This flow is a read-only readiness check against existing status artifacts.
- It does not run discovery/sync/transcription/GPT report generation by default.
- Avoid changing command path/semantics unless explicitly approved.
- Supersedes prompt:
  - `docs/prompts/legacy_tuesday_report_prompt.md`
