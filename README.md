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

Per-show contract (API-like surface):
- Each show has its own stable pointer (`stable_pointer` in `shows.json`).
- Each show has its own status artifacts (`<stable_pointer_stem>_status.json|md`).
- Schedules can differ per show while preserving the same output contract.

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

# Tuesday verification report (writes artifacts/jack_mallers_show_weekly_report.md)
bash scripts/report_mallers_weekly_status.sh

# Generic, multi-show equivalents:
bash scripts/run_show_weekly.sh <show_key>
bash scripts/report_show_weekly_status.sh <show_key>

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

# Cost-controlled GPT report generation from transcript:
# default mode sends excerpt only (not full transcript)
.venv311/bin/python scripts/gpt_report_from_transcript.py \
  --transcript-path transcripts/jack_mallers_show/jack_mallers.md \
  --report-name gpt-bitreport-pods-all-YYYYMMDD-HHMM.md \
  --show-key jack_mallers_show

# full transcript mode (explicit opt-in only)
.venv311/bin/python scripts/gpt_report_from_transcript.py \
  --transcript-path transcripts/jack_mallers_show/jack_mallers.md \
  --report-name gpt-bitreport-pods-all-YYYYMMDD-HHMM.md \
  --show-key jack_mallers_show \
  --full-text
```

Timeline policy:
- Default local timeline is `America/Managua` (no DST drift).
- `--as-of` is optional and intended for historical debugging/replay.
- For live-heavy YouTube sources, sync applies a default maturity guard (`--min-episode-age-minutes 180`) to avoid unfinished captures.
- GPT bridge cost estimates are logged to `artifacts/cost-meter/bridge_cost_estimates.jsonl`.

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
