# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder section for upcoming changes.

## [0.2.1.1] - 2026-02-25

### Added
- Added explicit weekly run status artifacts:
  - `transcripts/jack_mallers_show/jack_mallers_status.json`
  - `transcripts/jack_mallers_show/jack_mallers_status.md`
- Added GPT QA request artifact for every run:
  - `transcripts/<show_key>/<stable_pointer_stem>_gpt_review_request.md`
- Added weekly helper scripts:
  - `scripts/run_mallers_weekly.sh`
  - `scripts/report_mallers_weekly_status.sh`
- Added generic multi-show weekly scripts:
  - `scripts/run_show_weekly.sh <show_key>`
  - `scripts/report_show_weekly_status.sh <show_key>`
- Added failure-stage classification and recommended next-action hints for weekly runs.

### Changed
- Sync now always emits run-level status artifacts on non-dry runs.
- Stable pointer updates only when the selected latest episode is successfully included.
- Version bumped to `0.2.1.1`.

## [0.2.1] - 2026-02-20

### Added
- Added YouTube caption cue parsing + overlap stitching before caption acceptance.
- Added caption quality gate heuristics (repetition/diversity/cue density) on top of minimum-word threshold.
- Added dual transcript companion outputs per episode: `*_plain.txt` and `*_segments.jsonl`.
- Added RSS-first source preference, media cache reuse, and source-policy CLI controls.
- Added Anchor RSS default for `jack_mallers_show` (`https://anchor.fm/s/e29097f4/podcast/rss`).

### Changed
- Sync now stores transcript artifact paths and source mode metadata in `index/processed.json`.
- Sync dedupes episodes by GUID and prefers richer source types (`rss_audio` before YouTube video).
- Version bumped to `0.2.1`.

## [0.2.0] - 2026-02-18

### Added
- Restored full podcast pipeline package (`bitpod/`) with CLI, discovery, sync, storage, indexing, and transcription provider modules.
- Added support for mixed feed strategies per show (`youtube` + optional `rss` list).
- Added source/media-type handling for YouTube video URLs and RSS enclosure media URLs.
- Added dry-run safety behavior that returns structured preview output without downloads/transcription.
- Added tests for episode filtering, feed URL extraction, and storage path utilities.

### Changed
- Sync now aggregates episodes from multiple feed URLs and deduplicates by GUID.
- Default show config now includes an `rss` feed list placeholder.
- Version bumped to `0.2.0`.

## [0.1.1] - 2026-02-18

### Added
- Added release discipline docs and changelog process scaffolding.

## [0.1.0] - 2026-02-18

### Added
- Initial repository bootstrap.

[Unreleased]: https://github.com/cjarguello/bitpod/compare/v0.2.1.1...HEAD
[0.2.1.1]: https://github.com/cjarguello/bitpod/compare/v0.2.1...v0.2.1.1
[0.2.1]: https://github.com/cjarguello/bitpod/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/cjarguello/bitpod/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/cjarguello/bitpod/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cjarguello/bitpod/releases/tag/v0.1.0
