# Weekly Automation Contract (Two-Track)

This runbook locks weekly scheduling to two track automations only.

## Goal

- Keep one stable legacy production track.
- Keep one experimental track isolated for intake/output iteration.
- Keep Friday legacy available as ad hoc, not as a standing weekly automation.

## Allowed Weekly Automations

1. `legacy_tuesday_track` (ACTIVE)
   - command: `bash scripts/run_legacy_tuesday_track.sh jack_mallers_show`
   - purpose: stable personal weekly report path
   - must emit Tuesday report + shared permalink contract
2. `experimental_track` (ACTIVE or PAUSED by choice)
   - command: `bash scripts/run_experimental_track.sh jack_mallers_show`
   - purpose: isolated experimental intake/output path
   - must emit intake snapshot with shared permalink contract

## Explicitly Not Weekly-Automated

- `legacy_friday_track` stays ad hoc:
  - `bash scripts/run_legacy_friday_track.sh jack_mallers_show`

## Deprecated / Duplicate Automation Policy

- Any paused duplicate Monday sync or Tuesday verify jobs are legacy debris.
- Do not unpause or clone those jobs.
- Replace mixed/ambiguous automation prompts with one of the two allowed tracks above.

## Deterministic Verification

Use these checks after automation edits:

```bash
make print-show-contract SHOW_KEY=jack_mallers_show
make track-status-check SHOW_KEY=jack_mallers_show
```

If both pass, the two-track contract is operational.
