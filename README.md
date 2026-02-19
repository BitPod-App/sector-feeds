# bitpod

Convert podcast and social-feed episodes into clean text transcripts for downstream BTC analysis and reporting.

## What This Repo Does

`bitpod` automates this workflow:

1. Discover and poll configured feeds.
2. Identify new episodes.
3. Select the best available source (audio/captions/media) based on policy.
4. Transcribe to clean text with consistent metadata.
5. Export transcripts in a deterministic structure for model consumption.

## What Works Today

- Jack Mallers Show processing path is implemented and serves as the validation baseline.
- RSS and YouTube feed ingestion are supported, with RSS prioritized for lower-cost audio ingestion.
- YouTube captions can be used when quality passes a minimum threshold.
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

# control source tradeoff policy: audio-first | balanced | caption-first | media-first
python -m bitpod sync --show jack_mallers_show --source-policy balanced

# forbid fallback to YouTube media downloads (fail fast if captions are unusable)
python -m bitpod sync --show jack_mallers_show --no-youtube-download

# require a stronger caption quality floor before accepting caption text
python -m bitpod sync --show jack_mallers_show --min-caption-words 180

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

- `jack_mallers_show`: confirmed working reference feed path with RSS-first priority.
- Additional source types and social feed integrations: planned next.

## Stable Pointer

- Stable transcript pointer file: `transcripts/jack_mallers_show/mallers_bitpod.md`
- It is updated from the latest successful transcript after sync.
- Avoid publishing direct transcript fetch URLs in public-facing docs.

## Operations

- Weekly runs should process only new episodes and skip known-successful ones.
- Failed episodes remain visible for retry.
- `gpt_status` metadata is set to `pending` on successful transcript creation.
- Paths and output formats remain stable to protect downstream automations.

## Versioning And Changes

- Versioning follows pre-1.0 SemVer (`0.x.y`).
- Change history lives in [CHANGELOG.md](CHANGELOG.md).
