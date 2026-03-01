# Feed Identity Contract (Lightweight)

This repository currently implements a lightweight feed identity policy that is compatible with RSS-first canonical mapping.

## Canonical Identity

- Canonical feed identity: `sector_feed_id` (RSS-canonical when available).
- Platform/source identity: `sector_feed_source_id` (platform-specific unit such as `youtube_playlist_id` or `spotify_show_id`).
- Canonical episode identity: `feed_episode_id` (GUID-first when available).
- Platform-specific IDs remain secondary mapping keys.
- Canonical catalog permalink path: `/antenna/sector-feeds/{sector_feed_id}`.

## Feed Unit Rule

- Selectable feed unit is `series/playlist/feed`, not whole channel.
- Public artifacts include:
  - `series_is_feed_unit`
  - `feed_unit_type`

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
