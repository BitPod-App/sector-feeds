# Experimental Weekly BTC Gate Runbook

## Intent

Sandbox the GPT "self-improved" weekly workflow and convert it into deterministic gate artifacts.

## Canonical ad hoc flow

0. Optional staged control surface:

```bash
# stage 1: collect-only intake snapshot
bash scripts/experimental_weekly_ctl.sh collect --show jack_mallers_show

# stage 2: process-only (updates transcript/pointer/permalink if needed)
bash scripts/experimental_weekly_ctl.sh process --show jack_mallers_show
```

1. Generate strict weekly report text using:
   - `tools/chatgpt-prompts/weekly-btc/weekly-btc-prompts.md`
   - primary sections: `0`, `1`, `2`, `7`
2. Save report markdown to a local path (example: `artifacts/gpt-bitreports/strict_weekly_btc.md`).
3. Build deterministic bundle:

```bash
python3 scripts/generate_weekly_critical_bundle.py \
  --report-md artifacts/gpt-bitreports/strict_weekly_btc.md \
  --output-json artifacts/private/weekly_bundles/weekly_critical_bundle.json
```

4. Run bitregime gate:

```bash
python3 /Users/cjarguello/BitPod-App/bitregime-core/scripts/gate_weekly_bundle.py \
  --bundle-json /Users/cjarguello/BitPod-App/bitpod/artifacts/private/weekly_bundles/weekly_critical_bundle.json \
  --output-json /Users/cjarguello/BitPod-App/bitregime-core/artifacts/gates/weekly_bundle_gate_status.json
```

## Canonical outputs

- `artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json`
  - includes `shared_permalink_contract` (same permalink intake/discovery/status/transcript URLs used by legacy track when available)
- `artifacts/runs/experimental_track/jack_mallers_show/<timestamp>__summary.md`
- `artifacts/runs/experimental_track/jack_mallers_show/<timestamp>__status.json`
- `artifacts/private/weekly_bundles/weekly_critical_bundle.json`
- `/Users/cjarguello/BitPod-App/bitregime-core/artifacts/gates/weekly_bundle_gate_status.json`
- Prompt: `docs/prompts/experimental_weekly_gate_single_prompt.md`

## Success criteria

- Bundle emitted with contract `weekly_critical_bundle.v1`
- Gate emitted with contract `weekly_bundle_gate.v1`
- `gate_status` explicitly set (`COMPLETE` or `INCOMPLETE`)

## Notes

- This is experimental and should remain ad hoc by default.
- Do not use this flow to replace legacy Tuesday behavior yet.
- `experimental_weekly_ctl.sh` is a transitional decoupled wrapper, not the final engine CLI.
- `collect` is fail-closed and emits a local snapshot even when network discovery is unavailable.
- Experimental track should share the same permalink/status contract surface as legacy, but it remains the heavier evaluation lane.
- Supersedes prompt:
  - `docs/prompts/experimental_weekly_btc_gate_prompt.md`
