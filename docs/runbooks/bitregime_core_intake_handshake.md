# bitregime-core Intake Handshake (`sector-feeds` Consumer via `bitpod` Namespace)

This runbook locks the `sector-feeds`-facing intake handshake for the first thin slice of `bitregime-core`, using the current `bitpod` Python package namespace inside `sector-feeds`.

Current operations mode:

- default required validation target: `bitregime_core_intake.v2`
- rollback diagnostic path available: `bitregime_core_intake.v1`
- daily ops runbook: `docs/runbooks/intake_gate_daily_ops.md`

## Scope

- Keep legacy + experimental weekly report tracks unchanged.
- Accept a minimal intake artifact from `bitregime-core`.
- Use deck processing-state markers in `index/deck_state.json` to avoid duplicate episode handling.

## Intake Contract (current `sector-feeds` consumer expectation)

The current `sector-feeds` consumer expects one JSON artifact per feed intake run with this contract:

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
| `canonical_episode_id` | No | string | Yes | If omitted, the current `sector-feeds` consumer derives canonical ID from `sector_feed_id + feed_episode_id`. |

Canonical sample artifact:

- `docs/architecture/bitregime_core_intake_v1_example.json`

## Contract Evolution + Compatibility Policy

- Current latest contract: `bitregime_core_intake.v2`
- Current `sector-feeds` consumer reader mode: `backward_compatible_reader_fail_closed_on_unknown_major`
- Supported versions right now: `bitregime_core_intake.v1`, `bitregime_core_intake.v2`
- Unknown/newer contract versions fail closed at handshake validation.
- Contract evolution rule:
  - Additive fields may be introduced in new versions.
  - Required field removals/renames require a new contract version and matching bitpod validator update.

### Validator Readiness Checklist (Before Supporting `v2`)

Use this checklist before declaring `bitregime_core_intake.v2` support in the current `sector-feeds` consumer:

1. Update validator constants:
- add `bitregime_core_intake.v2` to supported versions in `bitpod/core_intake_handshake.py`.

2. Update validation rules:
- encode any new required top-level and episode fields.
- keep explicit fail-closed behavior for unknown major versions.

3. Expand tests:
- add `v2` happy-path payload test.
- add `v2` invalid payload tests for each new required rule.
- keep `v1` compatibility tests passing.

4. Verify handshake command flow:
- run:
  - `bash scripts/check_bitregime_core_intake_handshake.sh <v2_intake_json_path> <deck_id>`
- confirm deterministic output JSON and `contract_ok: true` for valid `v2`.

5. Update docs:
- update this runbook compatibility section with `v2` status.
- keep copy/paste compatibility note templates aligned with validator behavior.

Processing-state semantics used by the current `sector-feeds` consumer in this handshake:

- terminal states skipped for intake planning: `processed`, `consumed`, `done`, `failed`, `error`, `skipped`
- non-terminal episodes are candidate rows unless already consumed in deck state

## Adapter + Validation Command Flow (Ad Hoc)

From `/Users/cjarguello/bitpod-app/sector-feeds`:

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
- Output (`sector-feeds` consumer): `artifacts/coordination/bitregime_intake_handshake_jack_mallers_show_deck_weekly_btc.json`
- Processing state store: `index/deck_state.json`

## Deterministic Validation Output

`scripts/check_bitregime_core_intake_handshake.sh` writes deterministic output JSON with:

- `validation_output_version`
- `validator_version`
- `compatibility_policy`
- `payload_fingerprint_sha256`
- `contract_ok`
- `contract_errors` (sorted)
- `pending` rows sorted by `published_at_utc`

## M-4 Rollout Gates (Historical Cutover Record)

Producer default must not switch from `bitregime_core_intake.v1` to `bitregime_core_intake.v2` until all gates below are satisfied.

1. Parallel validation soak window:
- minimum window: 14 consecutive calendar days
- on each run, keep `v1` as required gate and enable advisory parallel `v2`:
  - `BITPOD_INTAKE_ENABLE_V2_PARALLEL_GATE=1 bash scripts/check_bitregime_core_intake_handshake.sh <intake_json_path> <deck_id>`

2. Required pass metrics over soak window:
- `v1` required gate pass rate: 100%
- `v2` parallel gate pass rate: 100%
- `v2` parallel contract error count: 0 on all observed runs

3. Required schema/format conformance (no exceptions):
- producer emits `contract_version: bitregime_core_intake.v2`
- producer emits `context.deck_id` and `context.user_id`
- all required `v2` timestamps are strict UTC ISO-8601 with `Z` suffix
- `processing_state.status` values are in the allowed enum only
- `processing_state.attempt_count` is integer `>= 0` for all episodes
- if present, `processing_state.reason_code` and `processing_state.last_error` are strings

4. Promotion decision gate:
- create an M-4 rollout note that includes:
  - soak window start/end dates (absolute dates)
  - total run count observed
  - proof that `v1` and `v2` metrics both met thresholds
  - explicit operator approval to switch producer default to `v2`

5. Cutover safety rule:
- after producer default switch to `v2`, keep the `v1` validation path available for rollback diagnostics until post-cutover stability review is complete.

## Compatibility Notes (Copy/Paste Templates)

No producer change:

```text
Compatibility Note (Intake Handshake)
- contract_version: bitregime_core_intake.v1 (unchanged)
- required fields: unchanged
- validator/output changes: consumer-side only
- action for Core Intake Thin Slice thread: none
- action for `sector-feeds` ops thread: none
```

Producer required change:

```text
Compatibility Note (Intake Handshake)
- contract_version: bitregime_core_intake.v1
- required producer delta: <field/rule change>
- effective date: <YYYY-MM-DD>
- action for Core Intake Thin Slice thread: update producer artifact to include new required field/rule
- action for `sector-feeds` ops thread: none unless handshake check command/paths changed
```

Breaking major change:

```text
Compatibility Note (Intake Handshake)
- new contract_version: bitregime_core_intake.v2
- compatibility mode: fail-closed for unknown major until validator update lands
- action for Core Intake Thin Slice thread: do not switch default producer to v2 until the current `sector-feeds` validator supports v2
- action for `sector-feeds` ops thread: none unless explicit consumer command changes are required
```

## Weekly Track Stability Note

This handshake path is additive only:

- it does not modify `scripts/run_show_weekly.sh`
- it does not modify `scripts/run_legacy_tuesday_track.sh`
- it does not modify `scripts/run_experimental_track.sh`

The current weekly pipelines continue to use existing permalink/status contracts.
