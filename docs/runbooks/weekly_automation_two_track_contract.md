# Weekly Automation Contract

This runbook locks weekly scheduling to one fetch automation plus two report-track automations.

## Goal

- Keep one fetch-only automation that refreshes transcript/status/permalink artifacts without GPT coupling.
- Keep one stable legacy production track.
- Keep one experimental track isolated for intake/output iteration.
- Keep Friday legacy available as ad hoc, not as a standing weekly automation.

## Allowed Weekly Automations

1. `mallers_weekly_fetch` (ACTIVE)
   - workflow: `.github/workflows/mallers-weekly-fetch.yml`
   - command: `bash scripts/run_mallers_weekly.sh`
   - purpose: refresh transcript/status/permalink artifacts without GPT reporting by default
   - must emit:
     - stable current-state artifacts under `transcripts/jack_mallers_show/`
     - unique per-run operator/debug artifacts under `artifacts/runs/mallers_weekly_fetch/jack_mallers_show/`
2. `legacy_tuesday_track` (ACTIVE)
   - command: `bash scripts/run_legacy_tuesday_track.sh jack_mallers_show`
   - purpose: stable personal weekly report path
   - must emit Tuesday report + shared permalink contract
3. `experimental_track` (ACTIVE or PAUSED by choice)
   - command: `bash scripts/run_experimental_track.sh jack_mallers_show`
   - purpose: isolated experimental intake/output path
   - must emit intake snapshot with shared permalink contract

## Explicitly Not Weekly-Automated

- `legacy_friday_track` stays ad hoc:
  - `bash scripts/run_legacy_friday_track.sh jack_mallers_show`

## Deprecated / Duplicate Automation Policy

- Any duplicate fetch or Tuesday verify jobs are legacy debris.
- Do not unpause or clone ambiguous Monday sync jobs.
- Replace mixed/ambiguous automation prompts with one of the allowed automations above.

## Deterministic Verification

Use these checks after automation edits:

```bash
make print-show-contract SHOW_KEY=jack_mallers_show
make track-status-check SHOW_KEY=jack_mallers_show
```

If both pass, the weekly automation contract is operational.

## Interpretation Rule

- `transcripts/jack_mallers_show/jack_mallers_status.json` is the stable latest-known-state contract.
- `artifacts/runs/<track>/jack_mallers_show/<timestamp>__summary.md` is the per-run debugging/evidence surface.
- Do not treat the stable status file as a historical run log.
- When debugging a specific weekly automation execution, prefer the unique per-run summary first, then use the stable status artifact to confirm the current retained state.
