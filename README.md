# bitpod

Minimal pipeline to discover podcast/video feeds, ingest new episodes, transcribe media with OpenAI, and commit transcript Markdown files into this repo.

## What this v1 does

- Supports show config for `jack_mallers_show` out of the box.
- Discovers YouTube RSS feed URL from a channel handle/URL.
- Supports multiple feed sources per show (`youtube` + optional `rss` list).
- Polls feed entries and skips episodes already marked successful.
- Handles source types cleanly:
  - YouTube video source URLs -> audio download via `yt-dlp`
  - RSS enclosure media URLs (audio/video) -> direct media download
- Transcribes media via OpenAI's official Python SDK.
- Stores one Markdown transcript per episode under `transcripts/<show>/<year>/`.
- Tracks episode processing outcomes in `index/processed.json`.

## Project layout

- `shows.json` (generated): show identities + discovered feed URLs
- `index/processed.json` (generated): episode processing status index
- `transcripts/<show_key>/<YYYY>/<YYYY-MM-DD>__<episode-slug>.md`

## MacBook-friendly setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Set your API key (do not commit it):

```bash
export OPENAI_API_KEY="your_key_here"
```

Optional: override where bitpod reads/writes repo files (`shows.json`, `index/`, `transcripts/`):

```bash
export BITPOD_ROOT="/path/to/bitpod"
```

## Usage

Discover feeds for Jack Mallers Show:

```bash
python -m bitpod discover --show jack_mallers_show
```

Safe preview (no downloads/transcription/writes):

```bash
python -m bitpod sync --show jack_mallers_show --dry-run
```

Sync newest 3 episodes (default behavior):

```bash
python -m bitpod sync --show jack_mallers_show
```

Sync newest N episodes:

```bash
python -m bitpod sync --show jack_mallers_show --max-episodes 5
```

Sync only episodes from the last X days:

```bash
python -m bitpod sync --show jack_mallers_show --since-days 14
```

Optional: choose a transcription model:

```bash
python -m bitpod sync --show jack_mallers_show --model gpt-4o-mini-transcribe
```

## Versioning & releases

This project uses Semantic Versioning while pre-1.0 (`0.x.y`) for early-stage iteration:

- **PATCH (`0.1.x`)**: bug fixes, safety/reliability improvements, docs/tests changes.
- **MINOR (`0.x.0`)**: backward-compatible feature additions.
- **MAJOR (`1.0.0+`)**: breaking/stability milestone once interfaces become stable.

Release workflow (lightweight):

1. Update `bitpod/__init__.py` and `pyproject.toml` with the same version.
2. Add release notes to `CHANGELOG.md` under a new version heading.
3. Commit and create a PR.
4. Tag after merge.

## Architecture notes (low-cost discipline)

Current module boundaries are intentionally simple and separable:

- ingestion/discovery (`bitpod.discovery`, `bitpod.feeds`, `bitpod.sync`)
- source/media acquisition (`bitpod.audio`)
- transcription provider (`bitpod.transcribe.*`)
- persistence/index (`bitpod.storage`, `bitpod.indexer`, `bitpod.paths`)

## Notes

- `discover` currently fully supports YouTube RSS discovery and is structured for future Apple/Spotify→PodcastIndex expansion.
- Dry-run mode returns a structured `would_process` list and never downloads/transcribes.
- Failures are recorded per episode in `index/processed.json` and do not stop the run.
- Re-runs skip episodes with status `ok` and retry episodes marked `failed`.
- If a configured transcription model is unavailable/invalid, transcription retries once with `whisper-1`.
