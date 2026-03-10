# bitpod

Convert podcast and social-feed episodes into clean text transcripts for downstream BTC analysis and reporting.

## What This Repo Does

`bitpod` automates this workflow:

1. Discover and poll configured feeds.
2. Identify new episodes.
3. Choose the best available source (RSS audio, captions, or media) based on policy.
4. Transcribe and normalize text.
5. Export deterministic artifacts for model consumption.

## What Works Today

- Jack Mallers Show processing path is implemented and serves as the validation baseline.
- Feed discovery supports YouTube RSS URL extraction from channel inputs.
- Sync supports mixed feed strategy per show (`youtube` plus optional `rss` list), with RSS prioritized.
- Episode processing is idempotent: successful episodes are skipped on reruns.
- Transcript artifacts are written under `transcripts/<show>/<year>/` with status tracking in `index/processed.json`.
- Captions are parsed and stitched (de-overlap) before acceptance; low-quality captions fall back to media transcription.

## Why This Exists

Immediate goal: reliable transcript generation from high-signal feeds.
Primary consumer: GPT workflows that currently require clean text transcripts as input.

## Quickstart

```bash
# from repo root
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
export OPENAI_API_KEY="your_key_here"
```

Optional: override root path for generated artifacts.

```bash
export BITPOD_ROOT="/path/to/bitpod"
```

## Usage

```bash
# discover configured feed(s) for Jack Mallers Show
python -m bitpod discover --show jack_mallers_show

# preview only (no downloads/transcription/writes)
python -m bitpod sync --show jack_mallers_show --dry-run

# sync/transcribe newest episodes (default max: 3)
python -m bitpod sync --show jack_mallers_show

# choose source behavior
python -m bitpod sync --show jack_mallers_show --source-policy balanced

# restrict which feed families are eligible
python -m bitpod sync --show jack_mallers_show --feed-mode rss_preferred

# fail fast if youtube captions are low quality (no media download fallback)
python -m bitpod sync --show jack_mallers_show --no-youtube-download

# require a stronger caption quality floor
python -m bitpod sync --show jack_mallers_show --min-caption-words 300

# sync/transcribe newest N episodes
python -m bitpod sync --show jack_mallers_show --max-episodes 5

# process only recent episodes
python -m bitpod sync --show jack_mallers_show --since-days 14

# optional transcription model override
python -m bitpod sync --show jack_mallers_show --model gpt-4o-mini-transcribe
```

## Inputs And Outputs

Inputs
- Show/feed definitions in `shows.json`.
- Runtime config: `OPENAI_API_KEY` (required), `BITPOD_ROOT` (optional).

Outputs
- Transcript Markdown files in `transcripts/<show_key>/<YYYY>/`.
- Companion plain-text files: `*_plain.txt`.
- Companion structured segments: `*_segments.jsonl`.
- Weekly run status artifacts:
  - `transcripts/jack_mallers_show/jack_mallers_status.json`
  - `transcripts/jack_mallers_show/jack_mallers_status.md`
- Processing status index in `index/processed.json`.
- Discovered/normalized feed metadata in `shows.json`.

Artifact tracking policy:
- Runtime/cache outputs are local-only and git-ignored (for example: `cache/`, `.wrangler/`, `artifacts/public/`, `artifacts/private/`, cost logs, and feedback logs).
- Canonical transcript artifacts under `transcripts/` remain tracked unless explicitly changed by project policy.
- Before push, run `make audit` to enforce size guard + unit tests.

Per-show contract (API-like surface):
- Each show has its own stable pointer (`stable_pointer` in `shows.json`).
- Each show has its own status artifacts (`<stable_pointer_stem>_status.json|md`).
- Schedules can differ per show while preserving the same output contract.
- Public permalink publish (semi-paranoid): each show gets
  - `artifacts/public/permalinks/<opaque_id>/intake.md`
  - `artifacts/public/permalinks/<opaque_id>/transcript.md` (stable latest transcript permalink for GPT)
  - `artifacts/public/permalinks/<opaque_id>/latest.md`
  - `artifacts/public/permalinks/<opaque_id>/status.json`
  - `artifacts/public/permalinks/<opaque_id>/discovery.json`
  - with noindex/nofollow/noarchive + `robots.txt` disallow-all.
  - internal mapping remains private in `artifacts/private/public_permalink_manifest.json`.
  - feed identity/tags contract reference: `docs/architecture/feed_identity_contract.md`.

## Supported Feeds (Current)

- `jack_mallers_show`: confirmed working reference feed path.
- Additional source types and social feed integrations: planned next.

## Stable Pointer And Private GPT Workflow

Primary stable transcript pointer (Jack Mallers):
- `transcripts/jack_mallers_show/jack_mallers.md`

Raw GitHub URL:
- `https://raw.githubusercontent.com/cjarguello/bitpod/main/transcripts/jack_mallers_show/jack_mallers.md`

Note:
- If the repository is private, GPT cannot fetch the raw URL directly.
- Use local upload artifacts instead (`jack_mallers.md` plus `jack_mallers_status.md`).

How it updates:
1. Run `sync` successfully for `jack_mallers_show`.
2. The latest successful transcript is selected from `index/processed.json`.
3. `jack_mallers.md` is overwritten with that transcript content.
4. Commit and push changes to `main` so the raw URL serves the update.

Operational commands:

```bash
cd /Users/cjarguello/bitpod-app/bitpod
source .venv311/bin/activate
python -m bitpod discover --show jack_mallers_show
python -m bitpod sync --show jack_mallers_show --max-episodes 1
```

Weekly helper scripts:

```bash
# Monday run (newest 1 episode, status artifacts always written)
bash scripts/run_mallers_weekly.sh

# Optional: include GPT report generation in weekly run
WEEKLY_GPT_REPORT=1 bash scripts/run_mallers_weekly.sh

# Tuesday verification report (writes artifacts/jack_mallers_show_tuesday_report.md)
# - includes deterministic intake readiness checks for intake.md/latest.md/status.json/discovery.json
bash scripts/report_mallers_tuesday_status.sh

# One-shot legacy Tuesday track (sync + report + contract print)
bash scripts/run_legacy_tuesday_track.sh jack_mallers_show

# Friday verification report (writes artifacts/jack_mallers_show_friday_report.md)
bash scripts/report_mallers_friday_status.sh

# One-shot legacy Friday track (sync + report + contract print)
bash scripts/run_legacy_friday_track.sh jack_mallers_show

# One-shot experimental track (collect + process + contract print)
bash scripts/run_experimental_track.sh jack_mallers_show

# Force experimental track to use RSS only
BITPOD_FEED_MODE=rss_only bash scripts/run_experimental_track.sh jack_mallers_show

# Validate feed identity contract (IDs + canonical catalog path)
make feed-identity-check SHOW_KEY=jack_mallers_show

# Render one-page board for Tuesday/Friday/Experimental status
make track-status-board SHOW_KEY=jack_mallers_show

# Fast PASS/FAIL gate from board JSON (non-zero exit on failure)
make track-status-check SHOW_KEY=jack_mallers_show

# One-command fast operator preflight
make preflight SHOW_KEY=jack_mallers_show

# Release readiness gate (preflight + key tests)
make release-ready SHOW_KEY=jack_mallers_show

# Full daily operator cycle (all tracks + board + gate)
make ops-cycle SHOW_KEY=jack_mallers_show

# Optional DNS helpers (macOS networksetup)
make dns-set-fast
make dns-restore-default

# Full session helper (with DNS set/restore)
make today-run SHOW_KEY=jack_mallers_show

# Full session helper (without DNS changes)
make today-run-no-dns SHOW_KEY=jack_mallers_show

# Full final gate (today-run-no-dns + handoff refresh + live smoke)
make final-check SHOW_KEY=jack_mallers_show

# Refresh concise handoff snapshot
make handoff-refresh SHOW_KEY=jack_mallers_show

# Public smoke test against canonical URLs (HTTP + contract markers)
make smoke-public SHOW_KEY=jack_mallers_show

# Fail if status timestamp is older than threshold (default 9 days)
make stale-check SHOW_KEY=jack_mallers_show

# Quiet wrapper mode (compact output)
QUIET=1 make ops-cycle SHOW_KEY=jack_mallers_show

# Legacy weekly alias (writes artifacts/jack_mallers_show_weekly_report.md)
bash scripts/report_mallers_weekly_status.sh

# Track-specific runbooks/prompts:
# - docs/runbooks/legacy_tuesday_report.md
# - docs/prompts/legacy_tuesday_report_prompt.md
# - docs/runbooks/experimental_weekly_btc_gate.md
# - docs/prompts/experimental_weekly_btc_gate_prompt.md
# - docs/prompts/legacy_tuesday_single_prompt.md
# - docs/prompts/experimental_weekly_gate_single_prompt.md
# - docs/runbooks/report_tracks_short_vs_long_term.md
# - docs/runbooks/weekly_automation_two_track_contract.md
# - docs/runbooks/recovered_local_trash_report_assets_assessment.md
# - scripts/experimental_weekly_ctl.sh (transitional decoupled stage wrapper)

# Generic, multi-show equivalents:
bash scripts/run_show_weekly.sh <show_key>
bash scripts/report_show_weekly_status.sh <show_key> [weekly|tuesday|friday]

# bitregime-core intake handshake check (additive; does not change weekly tracks):
bash scripts/check_bitregime_core_intake_handshake.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc

# Make wrapper:
make intake-handshake-check SHOW_KEY=jack_mallers_show DECK_ID=deck_weekly_btc

# Runbook:
# - docs/runbooks/bitregime_core_intake_handshake.md

# Daily v2-default intake gate (machine+human artifacts + retained history):
make intake-gate-daily SHOW_KEY=jack_mallers_show DECK_ID=deck_weekly_btc

# One-command operator triage + rollback diagnostic path:
make intake-gate-triage SHOW_KEY=jack_mallers_show DECK_ID=deck_weekly_btc

# Deterministic weekly critical bundle (10-metric gate input):
python3 scripts/generate_weekly_critical_bundle.py \
  --report-md ../artifacts/recovery/2026-02-27/weekly_btc_strict_single_pass_7_artifact.md \
  --output-json artifacts/private/weekly_bundles/weekly_critical_bundle.json

# Ad hoc mode:
# - sync only if latest selected episode is not already processed
bash scripts/run_show_adhoc.sh <show_key>

# - record GPT feedback consumption for latest run
bash scripts/record_show_gpt_feedback.sh <show_key> <feedback_markdown_path>

# - verify run + GPT consumption + feedback linkage
bash scripts/verify_show_adhoc.sh <show_key>

# Unified operator commands (chat-friendly wrappers):
bash scripts/bitpod_status.sh [--show all|<show_key>] [--as-of "YYYY-MM-DD[ HH:MM]"]
bash scripts/bitpod_sync.sh [--show all|<show_key>] [--as-of "YYYY-MM-DD[ HH:MM]"] [--min-episode-age-minutes 180] [--trigger-cmd "<cmd>"]
bash scripts/bitpod_verify.sh [--show all|<show_key>] [--as-of "YYYY-MM-DD[ HH:MM]"] [--gpt-feedback-file <path>] [--gpt-note "<text>"]

# M-5 intake operations runbook:
# - docs/runbooks/intake_gate_daily_ops.md

# Operator guidance (MVP):
# - Primary flow: Status -> Sync -> Deploy
# - Sync now enforces strict parity checks (same gate as Verify) by default.
# - Verify remains useful as a standalone audit/recheck command or for recording GPT feedback linkage.

# Deploy public permalink artifacts to Cloudflare Pages (static only):
bash scripts/deploy_public_permalinks_pages.sh [project_name] [branch]

# Paranoid-public Cloudflare hardening checklist:
# - custom domain + AI crawler controls + bot policy
# - see CLOUDFLARE_PARANOID_PUBLIC_CHECKLIST.md

# Cost-controlled GPT report generation from transcript:
# default mode sends excerpt only (not full transcript)
.venv311/bin/python scripts/gpt_report_from_transcript.py \
  --transcript-path transcripts/jack_mallers_show/jack_mallers.md \
  --report-name gpt-bitreport-pods-all-YYYYMMDD-HHMMSS.md \
  --show-key jack_mallers_show

# full transcript mode (explicit opt-in only)
.venv311/bin/python scripts/gpt_report_from_transcript.py \
  --transcript-path transcripts/jack_mallers_show/jack_mallers.md \
  --report-name gpt-bitreport-pods-all-YYYYMMDD-HHMMSS.md \
  --show-key jack_mallers_show \
  --full-text

# Repo hygiene guard (tracked file size limits):
bash scripts/check_repo_size.sh

# Combined local audit:
make audit
```

Timeline policy:
- Default local timeline is `America/Managua` (no DST drift).
- `--as-of` is optional and intended for historical debugging/replay.
- For live-heavy YouTube sources, sync applies a default maturity guard (`--min-episode-age-minutes 180`) to avoid unfinished captures.
- GPT bridge cost estimates are logged to:
- local: `artifacts/cost-meter/bridge_cost_estimates.jsonl`
- shared tools source of truth: `/Users/cjarguello/bitpod-app/tools/artifacts/cost-meter/cost_events.jsonl`

Shared cost summary (all repos/commands that write to tools meter):
```bash
/Users/cjarguello/bitpod-app/tools/costs/cost_ctl.py
```

Weekly cost guardrails (automation-friendly):
- `run_show_weekly.sh` executes cost guard checks when caps are set via env.
- Defaults are auto-loaded from `scripts/bitpod_budget.env` (or optional override file `.bitpod_budget.env` at repo root).
- Supported env vars:
- `COST_SOURCE` (example: `bitpod.gpt_report_from_transcript`)
- `COST_WINDOW_HOURS` (default from tools CLI is 24)
- `COST_RUN_WARN`, `COST_RUN_FAIL`
- `COST_DAILY_WARN`, `COST_DAILY_FAIL`
- `COST_WARN_EXIT_0=1` to keep warning status non-blocking

Governance metadata (optional, status artifact only):
- Sync can embed spec-lock/provenance metadata into `<stable_pointer_stem>_status.json|md`.
- Default tuple: `origin_actor=OTHER`, `authority_state=PROPOSAL`.
- Fast setup: `cp .bitpod_runtime.env.example .bitpod_runtime.env` and edit values.
- Weekly scripts auto-load `.bitpod_runtime.env` when present.
- Optional env vars:
- `BITPOD_ORIGIN_ACTOR` (`CJ|GPT|CODEX|TAYLOR|HUMAN_TEAM|OTHER`)
- `BITPOD_AUTHORITY_STATE` (`PROPOSAL|CJ_ENDORSED|TEAM_ENDORSED|CJ_OVERRIDE`)
- `BITPOD_EXPANSION_GATE` (default `BLOCKED`)
- `BITPOD_SPEC_LOCK_ORIGINAL_ASK`
- `BITPOD_SPEC_LOCK_SUCCESS_CRITERIA` (comma-separated)
- `BITPOD_SPEC_LOCK_OUT_OF_SCOPE` (comma-separated)
- `BITPOD_BASELINE_REFS` (comma-separated)
- Soft override guard inputs (non-blocking visibility):
- `BITPOD_OVERRIDE_CONFLICT` (`1/true/yes/on`)
- `BITPOD_OVERRIDE_CONFLICT_NOTE`
- `BITPOD_OVERRIDE_IMPACTED_DECISION`
- `BITPOD_OVERRIDE_BROADCAST_NOTE`

Cadence policy:
- Unknown-cadence shows should be checked frequently (scan model), but processing remains idempotent: if latest is already transcribed and pointer-ready, ad hoc sync skips work.

## Roadmap (Near Term)

1. Confirm stable weekly transcript fetch/transcribe behavior for Jack Mallers Show.
2. Expand support across multiple feed/source types.
3. Standardize transcript cleanliness for downstream BTC scoring/reporting ingestion.
4. Add lightweight reporting outputs once transcript reliability is consistently high.

## Operations

- Weekly runs should process only new episodes and skip known-successful ones.
- Failed episodes should remain visible for retry.
- Paths and output formats should remain stable to protect downstream automations.

## Versioning And Changes

- Versioning follows pre-1.0 SemVer (`0.x.y`).
- Change history lives in [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the local quality gate and pre-push checklist.
