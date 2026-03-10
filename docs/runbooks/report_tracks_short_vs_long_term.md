# Report Tracks: Short-Term vs Long-Term

## Short-term (now)

- Keep two scheduled automation tracks:
  - `legacy_tuesday_track` (stable personal-use)
  - `experimental_track` (isolated experimental flow; can be ACTIVE or PAUSED)
- Keep legacy Friday as ad hoc-only:
  - `bash scripts/run_legacy_friday_track.sh jack_mallers_show`
- Keep them isolated (separate runbooks, prompts, outputs).
- Keep both tracks consuming the same permalink contract when available:
  - `public_permalink_transcript_url`
  - `public_permalink_status_url`
  - `public_permalink_discovery_url`
- Single launch reference:
  - `docs/prompts/weekly_tracks_quickstart.md`
- Weekly automation contract reference:
  - `docs/runbooks/weekly_automation_two_track_contract.md`

## Current operator contract

### Legacy Tuesday (stable)

```bash
bash scripts/run_show_weekly.sh jack_mallers_show
bash scripts/report_mallers_tuesday_status.sh
bash scripts/print_show_contract.sh jack_mallers_show
```

Outputs:
- `artifacts/jack_mallers_show_tuesday_report.md`
- `transcripts/jack_mallers_show/jack_mallers_status.json`

Operator note:
- legacy wrappers now emit `HEAVY_WORK_REQUIRED=true|false` before deciding whether sync work is needed

### Network toggle (optional)

If DNS instability slows network steps, use:

```bash
make dns-set-fast
# later, restore defaults
make dns-restore-default
```

### Experimental (ad hoc)

```bash
bash scripts/experimental_weekly_ctl.sh collect --show jack_mallers_show
bash scripts/experimental_weekly_ctl.sh process --show jack_mallers_show
```

Outputs:
- `artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json`
  - includes `shared_permalink_contract` (same permalink contract as legacy status JSON)
  - includes `feed_mode`

Policy note:
- experimental defaults to `BITPOD_FEED_MODE=rss_preferred`
- use `BITPOD_FEED_MODE=all` only when YouTube fallback is intentionally desired

## Long-term (target)

- Merge into one orchestrated task only after experimental track is reliable.
- Candidate merged behavior:
  1. intake check
  2. bounded remediation/recheck
  3. output report + deterministic gate artifact

## Merge prerequisites

- Experimental run passes repeatedly with deterministic outputs.
- Input/output contract is versioned and documented.
- Legacy Tuesday output quality is not degraded by merge.
