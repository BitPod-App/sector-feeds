# Recovered Local Trash: Weekly Report Assets Assessment

## Scope

Assessment of potentially useful report-related files found under:

- `/Users/cjarguello/BitPod-App/local-workspace/local-trash-delete`

Focus: prompts/templates and GPT-report-output-relevant contracts.

## High-value recovered asset

- Source: `/Users/cjarguello/BitPod-App/local-workspace/local-trash-delete/local-disposed-20260227__local-references__local-agents__local-taylor__weekly-report-template.md`
- Value: high
- Why:
  - provides a deterministic report contract
  - includes explicit verification ledger and artifact requirements
  - aligns with fail-closed and reproducibility goals

## What this recovered template gives us

1. Clear report sections:
   - report metadata
   - regime call
   - factor weights + deltas
   - event lifecycle table
   - verification ledger
   - score decomposition
   - risks/watchlist

2. Determinism and audit controls:
   - required artifact index
   - determinism checklist
   - fail-closed notes

3. Useful for experimental track:
   - helps stabilize "corrupted/self-improved" report shape
   - does not require changing legacy Tuesday flow

## What was not found in local-trash

- No separate runnable prompt pair explicitly labeled:
  - "legacy Tuesday prompt"
  - "corrupted Friday prompt"
- No obvious deleted GPT output corpus dedicated to those two named tracks.

## Mapping to current system

| Recovered template element | Current location | Status |
| --- | --- | --- |
| deterministic weekly strict report concept | `tools/chatgpt-prompts/weekly-btc/weekly-btc-prompts.md` | present |
| deterministic bundle contract | `bitpod/scripts/generate_weekly_critical_bundle.py` | present |
| deterministic gate output | `bitregime-core/scripts/gate_weekly_bundle.py` | present |
| canonical legacy Tuesday operational report | `bitpod/scripts/report_show_weekly_status.sh ... tuesday` | present |
| explicit "legacy vs experimental" runbooks/prompts | `bitpod/docs/runbooks/*` and `bitpod/docs/prompts/*` | present |

## Recommended use (immediate)

1. Keep legacy Tuesday unchanged:
   - use `legacy_tuesday_report` runbook/prompt only.

2. Use recovered template as structure target for experimental output:
   - keep experimental ad hoc.
   - standardize experimental report markdown headings to the recovered template.

3. Keep deterministic gate as source of truth for experimental pass/fail:
   - `weekly_critical_bundle.json`
   - `weekly_bundle_gate_status.json`

## Short-term decision

- Do not attempt to resurrect old mixed automations from trash artifacts.
- Treat recovered template as a structural guide, not an automation contract.
