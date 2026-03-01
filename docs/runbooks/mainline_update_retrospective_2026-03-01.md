# Mainline Update Retrospective (2026-03-01)

## Context

This repo received direct-to-`main` updates (no PR merge objects) for M-5 intake hardening and T3 cleanup slices.

## Direct-to-main commits

- `e8ec358` - `feat(ops): harden m5 v2 intake gate with policy, drift, and taylor context`
- `7056943` - `feat(core): add intake/storage/sync contract support`
- `1a1ed0b` - `feat(ops): add track automation and status tooling`
- `3d24b1b` - `docs(ops): document weekly tracks and intake handshake workflows`

## Segmented summary

### M-5 hardening

- policy-as-code: `milestones/m5_policy.json`
- daily status contract + drift validation: `scripts/run_intake_gate_daily.sh`, `bitpod/intake_gate_policy.py`
- daily artifacts:
  - `artifacts/coordination/intake_gate_daily_status.json`
  - `artifacts/coordination/intake_gate_daily_summary.md`
  - `artifacts/coordination/intake_gate_daily_drift_report.md`
  - `artifacts/coordination/m5_tracker.md`
- workflow automation: `.github/workflows/intake-gate-daily.yml`
- taylor keepalive/autopost helpers:
  - `scripts/taylor_runtime_keepalive.sh`
  - `scripts/taylor_autopost_intake_context.sh`

### T3-A core

- core intake/storage/sync contract support:
  - `bitpod/intake.py`
  - `bitpod/storage.py`
  - `bitpod/sync.py`
- contract/input alignment:
  - `shows.json`
- tests:
  - `tests/test_intake.py`
  - `tests/test_storage.py`

### T3-B ops tooling

- added automation/status scripts for legacy/experimental tracks, board checks, smoke/stale checks, and feed identity validation under `scripts/`.

### T3-C docs/interfaces

- added prompts + runbooks + architecture docs under `docs/`
- updated interface surfaces:
  - `Makefile`
  - `README.md`
  - `docs/runbooks/bitregime_core_intake_handshake.md`
  - `scripts/run_show_weekly.sh`
  - `scripts/report_show_weekly_status.sh`
  - `scripts/deploy_public_permalinks_pages.sh`

## Validation snapshot

- `python3 -m unittest tests.test_intake tests.test_storage` passed
- `python3 -m unittest tests.test_core_intake_handshake tests.test_intake_gate_policy` passed
- track status render/check smoke passed
- intake gate daily run passed with:
  - `contract_ok: true`
  - `status_contract_ok: true`
  - `drift_ok: true`
  - close-ready marker true (`>=3` greens)

## Historical context pattern

For future PR/commit notes that alter intake ops truth, include pointers to:

- `milestones/m5_policy.json`
- `artifacts/coordination/intake_gate_daily_status.json`
- `artifacts/coordination/intake_gate_daily_drift_report.md`
- `docs/runbooks/intake_gate_retrospective_learnings.md`
