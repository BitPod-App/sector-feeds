# Weekly Tracks Quickstart (Legacy + Experimental)

Use this as the single entrypoint for running GPT on either weekly track.

Scheduling policy:
- Weekly automations: `legacy_tuesday_track` and `experimental_track`
- Ad hoc only: `legacy_friday_track`

## Legacy Tuesday (stable)

Reference prompt:
- `docs/prompts/legacy_tuesday_single_prompt.md`

Run commands:

```bash
# one-shot wrapper
bash scripts/run_legacy_tuesday_track.sh jack_mallers_show

# equivalent explicit sequence
bash scripts/run_show_weekly.sh jack_mallers_show
bash scripts/report_mallers_tuesday_status.sh
bash scripts/print_show_contract.sh jack_mallers_show
```

Primary output:
- `artifacts/jack_mallers_show_tuesday_report.md`
- `artifacts/runs/legacy_tuesday_track/jack_mallers_show/<timestamp>__summary.md`

Preflight behavior:
- wrapper emits `HEAVY_WORK_REQUIRED=true|false` before any heavy sync step
- if `false`, it skips the sync step and only uses the latest available status artifacts

## Legacy Friday (stable status check)

Reference prompt:
- `docs/prompts/legacy_friday_single_prompt.md`

Run commands:

```bash
# one-shot wrapper
bash scripts/run_legacy_friday_track.sh jack_mallers_show

# equivalent explicit sequence
bash scripts/run_show_weekly.sh jack_mallers_show
bash scripts/report_mallers_friday_status.sh
bash scripts/print_show_contract.sh jack_mallers_show
```

Primary output:
- `artifacts/jack_mallers_show_friday_report.md`

## Experimental Weekly Gate (ad hoc)

Reference prompt:
- `docs/prompts/experimental_weekly_gate_single_prompt.md`

Run commands:

```bash
# one-shot wrapper
bash scripts/run_experimental_track.sh jack_mallers_show

# equivalent explicit sequence
bash scripts/experimental_weekly_ctl.sh collect --show jack_mallers_show
bash scripts/experimental_weekly_ctl.sh process --show jack_mallers_show
bash scripts/print_show_contract.sh jack_mallers_show
```

Optional strict gate build:

```bash
bash scripts/experimental_weekly_ctl.sh render-experimental --report-md /absolute/path/to/strict_weekly_btc.md
```

Primary outputs:
- `artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json`
- `artifacts/runs/experimental_track/jack_mallers_show/<timestamp>__summary.md`
- `artifacts/private/weekly_bundles/weekly_critical_bundle.json` (if generated)
- `../bitregime-core/artifacts/gates/weekly_bundle_gate_status.json` (if generated)

Feed-policy default:
- experimental wrapper defaults `BITPOD_FEED_MODE=rss_preferred`
- accepted values: `all`, `rss_preferred`, `rss_only`

Preflight behavior:
- wrapper emits `HEAVY_WORK_REQUIRED=true|false` with reason before heavy work
- intake snapshot now records the effective `feed_mode`

## Shared contract URLs (canonical for both tracks)

```bash
bash scripts/print_show_contract.sh jack_mallers_show
```

Expected lines:
- `public_permalink_transcript_url=.../transcript.md`
- `public_permalink_status_url=.../status.json`
- `public_permalink_discovery_url=.../discovery.json`
