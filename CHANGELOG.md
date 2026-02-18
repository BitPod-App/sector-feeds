# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder section for upcoming changes.

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

[Unreleased]: https://github.com/cjarguello/bitpod/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/cjarguello/bitpod/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/cjarguello/bitpod/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/cjarguello/bitpod/releases/tag/v0.1.0
The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

## [0.1.1] - 2026-02-18
### Added
- Introduced changelog and basic release/version discipline documentation.
