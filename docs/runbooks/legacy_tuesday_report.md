# Legacy Tuesday Report Runbook

## Intent

Keep the original Tuesday personal-use readiness flow stable and predictable.

## Canonical ad hoc commands

```bash
# optional bounded freshness check first (no-op if already up-to-date)
bash scripts/run_show_adhoc.sh jack_mallers_show

# canonical legacy Tuesday report artifact
bash scripts/report_show_weekly_status.sh jack_mallers_show tuesday
```

## Canonical output

- `artifacts/jack_mallers_show_tuesday_report.md`
- `artifacts/runs/legacy_tuesday_track/jack_mallers_show/<timestamp>__summary.md`
- `artifacts/runs/legacy_tuesday_track/jack_mallers_show/<timestamp>__status.json`
- Prompt: `docs/prompts/legacy_tuesday_single_prompt.md`

## Success criteria

- `run_status` is `ok`
- `included_in_pointer` is `True`
- `run_is_recent` is `True`
- `intake_ready` is `True`

## Notes

- This flow is the stable "legacy" track.
- Legacy Tuesday should prefer `rss_preferred` over full-video sources when a quality transcript path already exists.
- Legacy Tuesday must record GPT consumption against the same `run_id` used for the transcript/permalink status contract.
- Avoid changing command path/semantics unless explicitly approved.
- Supersedes prompt:
  - `docs/prompts/legacy_tuesday_report_prompt.md`
