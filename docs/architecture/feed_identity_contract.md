# Feed Identity Contract (Current + Near-Term)

This repository currently implements a lightweight, feed-centric identity model with partial cross-source support.

Shared product-MVP architecture canon for the broader feed/stream model lives in:

- `/Users/cjarguello/BitPod-App/bitpod-docs/product-mvp/SECTOR_FEEDS_STREAM_MVP_ARCHITECTURE.md`

This file is the repo-local implementation contract and migration bridge.

## Current Canonical Implementation

- Canonical feed identity: `sector_feed_id`
- Current platform/feed-unit identity: `sector_feed_source_id`
- Canonical episode identity in repo contracts: `feed_episode_id`
- Generated stable episode identity: `canonical_episode_id`
- Current legacy personalization container term in code/contracts: `deck_id`
- Forward-looking personalization term accepted in contracts: `stream_id`

Today, `sector-feeds` is still feed-centric. It does not yet implement the full `channel_id -> sector_feed_id -> episode_id` model from shared canon.

## Near-Term Terminology Direction

- Canonical shared-product term for personalization: `stream_id`
- Backward-compatible implementation alias for now: `deck_id`
- Do not introduce a new generic `source_id` field

Rules:
- `deck_id` remains readable/writable in current code and runbooks until migration completes.
- `stream_id` should be preferred in new planning and contract design.
- New generic identity fields should be explicit, not overloaded.

## Top-Level Parent Taxonomy

Shared canon direction is:

- `channel_id`
  - top-level parent container
  - non-selectable
  - platform-agnostic label, not a promise that the provider literally uses the word "channel"

- `sector_feed_id`
  - selectable playlist / show / feed unit
  - current operational selection unit in this repo

- `episode_id`
  - intended future canonical episode object term
  - current implementation still uses `feed_episode_id` in most contracts

Repo status today:
- `channel_id` is not yet first-class in config or runtime contracts.
- `sector_feed_id` is first-class and stable.
- `episode_id` is not yet the runtime term; `feed_episode_id` still is.

## Provider Identity Policy

The intended durable parent identity pattern is:

- `channel_id` — internal canonical parent ID
- `platform` — `youtube`, `spotify`, `apple_podcasts`, `rss`
- `platform_channel_id` — immutable provider-native ID
- `display_handle` — handle/alias when available
- `display_slug` — human-readable slug/path helper when useful
- `canonical_url` — provider parent page URL
- `channel_name` — human label

Current implementation status:

### YouTube

Implemented today:
- immutable provider-native ID: `youtube_channel_id`
- handle helper: `youtube_handle`
- URL helper: `youtube_channel_url`

Policy:
- do not use the handle as the hard primary key
- use the immutable channel ID as anchor
- keep handle/URL as alias/discovery helpers

### Spotify / Apple Podcasts / RSS

Current repo support is partial:
- `sector_feed_source_id` exists as a feed-unit identity surface
- RSS feed URLs are stored as durable locators
- no normalized first-class parent identity object exists yet across all providers

## Episode Identity Policy

Current repo runtime contract:

- `feed_episode_id`
  - canonical internal episode identity in current contracts
  - GUID-first when available

- `source_episode_id`
  - provider/source-native episode identity when available

- `canonical_episode_id`
  - generated stable ID derived from `sector_feed_id + feed_episode_id`

Rules:
- preserve immutable provider-native episode IDs when available
- preserve human-readable titles/slugs only as helper metadata
- do not widen the use of generic `source_id`

## Feed Unit Rule

- Selectable feed unit is `series/playlist/feed`, not whole parent channel.
- Public artifacts include:
  - `series_is_feed_unit`
  - `feed_unit_type`

## Episode-Linked Asset Extension

Current first-class episode-linked assets are transcript-oriented:
- transcript markdown
- plain transcript text
- segment JSONL
- permalink/status/discovery surfaces

Near-term additive extension is expected for optional episode-linked assets such as:
- `slide_deck_url`
- `slide_text_artifact`
- `slide_asset_manifest`
- `slide_source_links`

This is not fully implemented yet, but the current storage/permalink model can absorb it as an additive extension.

## Tag Buckets (MVP)

- `sector_tags`
- `format_tags`
- `source_platform_tags`

Tags are kept flat and explicit for filtering. No deep taxonomy tree is required for MVP.

## bitregime-core Intake Handshake

For bitpod consumption of bitregime-core thin-slice intake artifacts, see:

- `docs/runbooks/bitregime_core_intake_handshake.md`

## URL Policy (YouTube)

Where possible, artifacts expose both:

- `canonical_video_url` (`watch?v=...`)
- `playlist_context_url` (`watch?v=...&list=...`)

This allows stable episode identity while preserving playlist-membership context.

## Playlist Membership Drift (Hook Only)

Current artifacts expose placeholders:

- `playlist_membership_status`
- `membership_last_seen_at_utc`
- `membership_miss_count`

These fields are intentionally present for future retirement logic without changing current ingest behavior.
