# bitpod

Convert podcast and social-feed episodes into clean text transcripts for downstream BTC analysis and reporting.

## What This Repo Does

`bitpod` automates this workflow:

1. Discover and poll configured feeds.
2. Identify new episodes.
3. Download media for each episode.
4. Transcribe media to clean text.
5. Export transcripts in a deterministic structure for model consumption.

## What Works Today

- Jack Mallers Show processing path is implemented and serves as the validation baseline.
- Feed discovery supports YouTube RSS URL extraction from channel inputs.
- Sync supports mixed feed strategy per show (`youtube` plus optional `rss` list).
- Episode processing is idempotent: successful episodes are skipped on reruns.
- Transcript artifacts are written under `transcripts/<show>/<year>/` with status tracking in `index/processed.json`.

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
- Processing status index in `index/processed.json`.
- Discovered/normalized feed metadata in `shows.json`.

## Supported Feeds (Current)

- `jack_mallers_show`: confirmed working reference feed path.
- Additional source types and social feed integrations: planned next.

## Stable Permalink For GPT Fetching

Primary stable transcript pointer (Jack Mallers):
- `transcripts/jack_mallers_show/mallers_bitpod.md`

Raw GitHub URL:
- `https://raw.githubusercontent.com/cjarguello/bitpod/main/transcripts/jack_mallers_show/mallers_bitpod.md`

How it updates:
1. Run `sync` successfully for `jack_mallers_show`.
2. The latest successful transcript is selected from `index/processed.json`.
3. `mallers_bitpod.md` is overwritten with that transcript content.
4. Commit and push changes to `main` so the raw URL serves the update.

Operational commands:

```bash
cd /Users/cjarguello/bitpod
source .venv311/bin/activate
python -m bitpod discover --show jack_mallers_show
python -m bitpod sync --show jack_mallers_show --max-episodes 1
git add transcripts/jack_mallers_show/mallers_bitpod.md index/processed.json shows.json
git commit -m "chore: refresh latest Jack Mallers transcript pointer"
git push origin main
```

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
