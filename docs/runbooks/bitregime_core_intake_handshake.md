# bitregime-core Intake Handshake (bitpod Consumer)

This runbook locks the bitpod-facing intake handshake for the first thin slice of `bitregime-core`.

## Scope

- Keep legacy + experimental weekly report tracks unchanged.
- Accept a minimal intake artifact from `bitregime-core`.
- Use deck processing-state markers in `index/deck_state.json` to avoid duplicate episode handling.

## Intake Contract (bitpod expectation)

Bitpod expects one JSON artifact per feed intake run with this contract:

- `contract_version`: `bitregime_core_intake.v1`
- `sector_feed_id`: canonical internal feed identity (RSS-first when available)
- `sector_feed_source_id`: platform/source identity (`youtube_playlist_id`, `spotify_show_id`, etc.)
- `episodes`: list of episode rows
  - required per row: `feed_episode_id`
  - required per row: `processing_state.status`
  - optional: `source_episode_id`, `published_at_utc`, `title`, `canonical_episode_id`

### Frozen Baseline: `bitregime_core_intake.v1`

This baseline is frozen for compatibility. Producers should treat these requirements as normative.

Top-level fields:

| Field | Required | Type | Nullable | Rules / Semantics |
|---|---|---|---|---|
| `contract_version` | Yes | string | No | Must equal `bitregime_core_intake.v1`. |
| `sector_feed_id` | Yes | string | No | Canonical internal feed identity (RSS-first when available). Non-empty after trim. |
| `sector_feed_source_id` | Yes | string | No | Platform/source unit identity (for example `youtube_playlist_id`, `spotify_show_id`). Non-empty after trim. |
| `episodes` | Yes | array<object> | No | Intake episode rows for this feed run. Empty array allowed. |
| `generated_at_utc` | No | string | Yes | Producer generation timestamp in UTC ISO-8601 when available. |

Episode row fields:

| Field | Required | Type | Nullable | Rules / Semantics |
|---|---|---|---|---|
| `feed_episode_id` | Yes | string | No | Canonical internal episode identity (GUID-first). Must be unique within `episodes`. Non-empty after trim. |
| `processing_state` | Yes | object | No | Processing status object for this episode. |
| `processing_state.status` | Yes | string | No | Non-empty status. Terminal statuses currently treated as already handled: `processed`, `consumed`, `done`, `failed`, `error`, `skipped`. |
| `source_episode_id` | No | string | Yes | Platform/source-native episode id. |
| `published_at_utc` | No | string | Yes | Episode publish timestamp in UTC ISO-8601 when available. |
| `title` | No | string | Yes | Human-readable episode title. |
| `canonical_episode_id` | No | string | Yes | If omitted, bitpod derives canonical ID from `sector_feed_id + feed_episode_id`. |

## Contract Evolution + Compatibility Policy

- Current latest contract: `bitregime_core_intake.v1`
- Bitpod reader mode: `backward_compatible_reader_fail_closed_on_unknown_major`
- Supported versions right now: `bitregime_core_intake.v1`
- Unknown/newer contract versions fail closed at handshake validation.
- Contract evolution rule:
  - Additive fields may be introduced in new versions.
  - Required field removals/renames require a new contract version and matching bitpod validator update.

Processing-state semantics used by bitpod in this handshake:

- terminal states skipped for intake planning: `processed`, `consumed`, `done`, `failed`, `error`, `skipped`
- non-terminal episodes are candidate rows unless already consumed in deck state

## Adapter + Validation Command Flow (Ad Hoc)

From `/Users/cjarguello/bitpod-app/bitpod`:

```bash
# 1) Validate bitregime-core intake contract and compute pending rows for a deck context.
bash scripts/check_bitregime_core_intake_handshake.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc

# 2) Inspect pending rows (from the generated output JSON path printed by step 1).
cat artifacts/coordination/bitregime_intake_handshake_jack_mallers_show_deck_weekly_btc.json

# 3) Mark one processed episode as consumed for this deck/feed context.
python3 scripts/deck_state_ctl.py mark \
  --deck-id deck_weekly_btc \
  --sector-feed-id jack_mallers_show \
  --feed-episode-id <feed_episode_id>

# 4) Re-run handshake check; pending_count should decrease or remain stable.
bash scripts/check_bitregime_core_intake_handshake.sh \
  ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
  deck_weekly_btc
```

## Example Paths

- Input (bitregime-core): `../bitregime-core/artifacts/intake/jack_mallers_show_intake.json`
- Output (bitpod): `artifacts/coordination/bitregime_intake_handshake_jack_mallers_show_deck_weekly_btc.json`
- Processing state store: `index/deck_state.json`

## Deterministic Validation Output

`scripts/check_bitregime_core_intake_handshake.sh` writes deterministic output JSON with:

- `validator_version`
- `compatibility_policy`
- `payload_fingerprint_sha256`
- `contract_ok`
- `contract_errors` (sorted)
- `pending` rows sorted by `published_at_utc`

## Weekly Track Stability Note

This handshake path is additive only:

- it does not modify `scripts/run_show_weekly.sh`
- it does not modify `scripts/run_legacy_tuesday_track.sh`
- it does not modify `scripts/run_experimental_track.sh`

The current weekly pipelines continue to use existing permalink/status contracts.
