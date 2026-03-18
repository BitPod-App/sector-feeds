# Mainline Update Retrospective (2026-03-18)

## Context

This repo received direct-to-`main` updates before a PR object was created for the stream-terminology and identity-contract bridge work.

This retrospective exists as the backfill PR record for that exception.

## Direct-to-main commits

- `7a88160` - `Bridge stream terminology and identity contracts`

Related shared-canon commit in `bitpod-docs`:

- `fdfe5aa` - `Add stream MVP architecture canon`

## Related Linear work

- [BIT-133 — Harden sector-feeds docs: README, AGENTS, permalink architecture, and operator runbooks](https://linear.app/bitpod-app/issue/BIT-133/harden-sector-feeds-docs-readme-agents-permalink-architecture-and)
- [BIT-136 — Stage stream_id migration and normalize provider parent identity in sector-feeds](https://linear.app/bitpod-app/issue/BIT-136/stage-stream-id-migration-and-normalize-provider-parent-identity-in)
- [BIT-137 — Add episode-linked slide deck asset model for sector-feeds and Jack Mallers](https://linear.app/bitpod-app/issue/BIT-137/add-episode-linked-slide-deck-asset-model-for-sector-feeds-and-jack)

## Summary

The direct-to-main slice intentionally stopped short of a full rename.

What landed:

- `stream_id` is now accepted as a forward alias for `deck_id` in the intake handshake validator/runtime.
- legacy `deck_id` behavior remains intact for backward compatibility.
- repo-local identity docs now align with the new shared canon direction.
- new transcript artifact metadata no longer emits fresh generic `source_id`; it emits `source_episode_id`.
- `shows.json` scaffold now documents the intended parent/provider identity shape without forcing runtime adoption yet.

## Deferred on purpose

The following did **not** land in the direct-to-main slice and remain tracked as follow-up work:

- full `deck_id` -> `stream_id` runtime/file/schema rename
- full `channel_id` parent-layer rollout
- `feed_episode_id` -> future `episode_id` normalization
- first-class episode-linked slide deck asset ingestion and permalink/report exposure

As those changes land, both shared canon and repo-local bridge docs may need additional updates:

- `/Users/cjarguello/BitPod-App/bitpod-docs/product-mvp/SECTOR_FEEDS_STREAM_MVP_ARCHITECTURE.md`
- `/Users/cjarguello/BitPod-App/sector-feeds/docs/architecture/feed_identity_contract.md`

## Validation snapshot

- `python3 -m unittest tests.test_deck_state tests.test_core_intake_handshake tests.test_storage` passed
- `bash scripts/check_feed_identity_contract.sh jack_mallers_show` passed
- `python3 -m py_compile bitpod/deck_state.py bitpod/core_intake_handshake.py bitpod/sync.py` passed
