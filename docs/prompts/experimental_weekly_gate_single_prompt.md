# Experimental Weekly Gate Single Prompt (Run + Evaluate)

Use this in the experimental ad hoc track to run and evaluate in one pass.

Run commands in this order:

```bash
# intake snapshot
bash scripts/experimental_weekly_ctl.sh collect --show jack_mallers_show

# process update (if needed)
bash scripts/experimental_weekly_ctl.sh process --show jack_mallers_show

# print shared permalink contract state
bash scripts/print_show_contract.sh jack_mallers_show
```

If strict report markdown exists, produce bundle+gate:

```bash
bash scripts/experimental_weekly_ctl.sh render-experimental --report-md /absolute/path/to/strict_weekly_btc.md
```

Primary artifacts:
- `artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json`
- `artifacts/private/weekly_bundles/weekly_critical_bundle.json` (if generated)
- `$WORKSPACE/bitregime-core/artifacts/gates/weekly_bundle_gate_status.json` (if generated)

```text
You are running and evaluating the experimental weekly BTC gate flow.

Inputs:
1) artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json
   - use `shared_permalink_contract` if present as the preferred intake/discovery source
2) artifacts/private/weekly_bundles/weekly_critical_bundle.json (if present)
3) $WORKSPACE/bitregime-core/artifacts/gates/weekly_bundle_gate_status.json (if present)
4) transcripts/jack_mallers_show/jack_mallers_status.json

Task:
1) Summarize intake state and freshness.
2) Confirm shared permalink contract values are present and non-empty:
   - public_permalink_transcript_url
   - public_permalink_status_url
   - public_permalink_discovery_url
3) If bundle+gate are present, report gate_status (COMPLETE/INCOMPLETE) and blocked items.
4) If bundle+gate are missing, output exactly what is missing and deterministic command sequence to produce them.
5) Provide minimum fix set for next run.

Rules:
- Use only provided artifacts.
- No external web research.
- Keep legacy Tuesday flow untouched.
- Keep recommendations command-level and deterministic.

Required output:
- intake_summary
- gate_status
- blocked_items
- missing_artifacts
- rerun_commands
- minimum_fix_set
```
