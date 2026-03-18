from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bitpod.core_intake_handshake import (
    CONTRACT_VERSION_V1,
    CONTRACT_VERSION_V2,
    VALIDATION_OUTPUT_VERSION,
    compatibility_policy,
    payload_fingerprint_sha256,
    pending_for_deck,
    pending_for_stream,
    validate_payload,
    validate_payload_v2,
)
from bitpod.deck_state import mark_consumed


class CoreIntakeHandshakeTests(unittest.TestCase):
    def _payload_v1(self) -> dict:
        return {
            "contract_version": CONTRACT_VERSION_V1,
            "generated_at_utc": "2026-02-28T00:00:00Z",
            "sector_feed_id": "jack_mallers_show",
            "sector_feed_source_id": "anchor:e29097f4",
            "episodes": [
                {
                    "feed_episode_id": "guid-1",
                    "source_episode_id": "spotify-1",
                    "processing_state": {"status": "new"},
                    "published_at_utc": "2026-02-20T00:00:00Z",
                },
                {
                    "feed_episode_id": "guid-2",
                    "source_episode_id": "spotify-2",
                    "processing_state": {"status": "processed"},
                    "published_at_utc": "2026-02-21T00:00:00Z",
                },
            ],
        }

    def _payload_v2(self) -> dict:
        return {
            "contract_version": CONTRACT_VERSION_V2,
            "generated_at_utc": "2026-02-28T00:00:00Z",
            "sector_feed_id": "jack_mallers_show",
            "sector_feed_source_id": "anchor:e29097f4",
            "context": {
                "deck_id": "deck_weekly_btc",
                "user_id": "user_123",
            },
            "episodes": [
                {
                    "feed_episode_id": "guid-1",
                    "canonical_episode_id": "jack_mallers_show:guid-1",
                    "source_episode_id": "spotify-1",
                    "published_at_utc": "2026-02-20T00:00:00Z",
                    "title": "Episode 1",
                    "processing_state": {
                        "status": "new",
                        "updated_at_utc": "2026-02-28T00:00:00Z",
                        "first_seen_at_utc": "2026-02-20T00:00:00Z",
                        "attempt_count": 0,
                    },
                }
            ],
        }

    def test_v1_valid_payload_passes(self) -> None:
        self.assertEqual(validate_payload(self._payload_v1(), contract_version=CONTRACT_VERSION_V1), [])

    def test_v1_existing_negative_cases_unchanged(self) -> None:
        payload = self._payload_v1()
        payload["sector_feed_source_id"] = ""
        payload["episodes"][0]["processing_state"] = {}
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:sector_feed_source_id", errors)
        self.assertIn("missing:episodes[0].processing_state.status", errors)

    def test_v2_default_output_is_v2(self) -> None:
        payload = self._payload_v1()
        errors = validate_payload(payload)
        self.assertIn(f"unsupported_contract_version:{CONTRACT_VERSION_V1}", errors)
        self.assertEqual(validate_payload(self._payload_v2()), [])

    def test_validate_payload_missing_episodes(self) -> None:
        payload = self._payload_v1()
        del payload["episodes"]
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:episodes", errors)

    def test_validate_payload_invalid_episodes_type(self) -> None:
        payload = self._payload_v1()
        payload["episodes"] = {"feed_episode_id": "guid-1"}
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:episodes", errors)

    def test_validate_payload_duplicate_feed_episode_id(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][1]["feed_episode_id"] = "guid-1"
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("duplicate:feed_episode_id:guid-1", errors)

    def test_validate_payload_missing_sector_feed_id(self) -> None:
        payload = self._payload_v1()
        payload["sector_feed_id"] = " "
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:sector_feed_id", errors)

    def test_validate_payload_invalid_episode_row_shape(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][0] = "not-an-object"
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("invalid_episode:0:not_object", errors)

    def test_validate_payload_missing_feed_episode_id(self) -> None:
        payload = self._payload_v1()
        del payload["episodes"][0]["feed_episode_id"]
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:episodes[0].feed_episode_id", errors)

    def test_validate_payload_missing_processing_state_object(self) -> None:
        payload = self._payload_v1()
        del payload["episodes"][0]["processing_state"]
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:episodes[0].processing_state", errors)

    def test_validate_payload_empty_processing_state_status(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][0]["processing_state"]["status"] = "  "
        errors = validate_payload(payload, contract_version=CONTRACT_VERSION_V1)
        self.assertIn("missing:episodes[0].processing_state.status", errors)

    def test_v2_valid_payload_passes(self) -> None:
        self.assertEqual(validate_payload_v2(self._payload_v2()), [])
        self.assertEqual(validate_payload(self._payload_v2(), contract_version=CONTRACT_VERSION_V2), [])

    def test_v2_stream_id_alias_passes_without_deck_id(self) -> None:
        payload = self._payload_v2()
        payload["context"] = {
            "stream_id": "stream_weekly_btc",
            "user_id": "user_123",
        }
        self.assertEqual(validate_payload_v2(payload), [])

    def test_v2_missing_generated_at_fails(self) -> None:
        payload = self._payload_v2()
        del payload["generated_at_utc"]
        errors = validate_payload_v2(payload)
        self.assertIn("missing:generated_at_utc", errors)

    def test_v2_missing_or_invalid_published_at_utc_fails(self) -> None:
        payload = self._payload_v2()
        del payload["episodes"][0]["published_at_utc"]
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].published_at_utc:utc_iso8601", errors)
        payload = self._payload_v2()
        payload["episodes"][0]["published_at_utc"] = "2026-02-20T00:00:00+00:00"
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].published_at_utc:utc_iso8601", errors)

    def test_v2_fractional_second_utc_z_formats_pass(self) -> None:
        payload = self._payload_v2()
        payload["generated_at_utc"] = "2026-02-28T00:00:00.1Z"
        payload["episodes"][0]["published_at_utc"] = "2026-02-20T00:00:00.12Z"
        payload["episodes"][0]["processing_state"]["updated_at_utc"] = "2026-02-28T00:00:00.123Z"
        payload["episodes"][0]["processing_state"]["first_seen_at_utc"] = "2026-02-20T00:00:00.123456Z"
        self.assertEqual(validate_payload_v2(payload), [])

    def test_v2_missing_or_invalid_processing_state_updated_at_utc_fails(self) -> None:
        payload = self._payload_v2()
        del payload["episodes"][0]["processing_state"]["updated_at_utc"]
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.updated_at_utc:utc_iso8601", errors)
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["updated_at_utc"] = "not-a-timestamp"
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.updated_at_utc:utc_iso8601", errors)

    def test_v2_missing_or_invalid_processing_state_first_seen_at_utc_fails(self) -> None:
        payload = self._payload_v2()
        del payload["episodes"][0]["processing_state"]["first_seen_at_utc"]
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.first_seen_at_utc:utc_iso8601", errors)
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["first_seen_at_utc"] = "2026-02-20"
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.first_seen_at_utc:utc_iso8601", errors)

    def test_v2_invalid_status_fails(self) -> None:
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["status"] = "unknown_state"
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.status:enum", errors)

    def test_v2_attempt_count_negative_fails(self) -> None:
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["attempt_count"] = -1
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.attempt_count:non_negative_int", errors)

    def test_v2_attempt_count_non_int_fails(self) -> None:
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["attempt_count"] = 1.5
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.attempt_count:non_negative_int", errors)

    def test_v2_reason_code_non_string_fails(self) -> None:
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["reason_code"] = 123
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.reason_code:string", errors)

    def test_v2_last_error_non_string_fails(self) -> None:
        payload = self._payload_v2()
        payload["episodes"][0]["processing_state"]["last_error"] = {"msg": "boom"}
        errors = validate_payload_v2(payload)
        self.assertIn("invalid:episodes[0].processing_state.last_error:string", errors)

    def test_v1_and_v2_validation_can_run_side_by_side(self) -> None:
        v1_errors = validate_payload(self._payload_v1(), contract_version=CONTRACT_VERSION_V1)
        v2_errors = validate_payload_v2(self._payload_v2())
        self.assertEqual(v1_errors, [])
        self.assertEqual(v2_errors, [])

    def test_pending_for_deck_filters_consumed_and_terminal_state(self) -> None:
        payload = self._payload_v1()
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            mark_consumed("deck-weekly-btc", "jack_mallers_show", "guid-1", path=deck_state_path)
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            self.assertEqual(pending, [])

    def test_pending_for_stream_alias_matches_deck_behavior(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][1]["processing_state"]["status"] = "new"
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            pending = pending_for_stream(payload, stream_id="stream-weekly-btc", deck_state_path=deck_state_path)
            ids = [row["feed_episode_id"] for row in pending]
            self.assertEqual(ids, ["guid-1", "guid-2"])

    def test_pending_for_deck_keeps_non_terminal(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][1]["processing_state"]["status"] = "new"
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            ids = [row["feed_episode_id"] for row in pending]
            self.assertIn("guid-1", ids)
            self.assertIn("guid-2", ids)

    def test_pending_for_deck_keeps_pending_and_skips_consumed_status(self) -> None:
        payload = self._payload_v1()
        payload["episodes"][0]["processing_state"]["status"] = "pending"
        payload["episodes"][1]["processing_state"]["status"] = "consumed"
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            ids = [row["feed_episode_id"] for row in pending]
            self.assertEqual(ids, ["guid-1"])
            self.assertEqual(pending[0]["processing_status"], "pending")

    def test_pending_for_deck_filters_all_terminal_states(self) -> None:
        payload = self._payload_v1()
        payload["episodes"] = [
            {"feed_episode_id": "e-consumed", "source_episode_id": "s1", "processing_state": {"status": "consumed"}},
            {"feed_episode_id": "e-done", "source_episode_id": "s2", "processing_state": {"status": "done"}},
            {"feed_episode_id": "e-error", "source_episode_id": "s3", "processing_state": {"status": "error"}},
            {"feed_episode_id": "e-failed", "source_episode_id": "s4", "processing_state": {"status": "failed"}},
            {"feed_episode_id": "e-processed", "source_episode_id": "s5", "processing_state": {"status": "processed"}},
            {"feed_episode_id": "e-skipped", "source_episode_id": "s6", "processing_state": {"status": "skipped"}},
            {"feed_episode_id": "e-pending", "source_episode_id": "s7", "processing_state": {"status": "pending"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            ids = [row["feed_episode_id"] for row in pending]
            self.assertEqual(ids, ["e-pending"])

    def test_payload_fingerprint_is_deterministic(self) -> None:
        payload = self._payload_v1()
        first = payload_fingerprint_sha256(payload)
        second = payload_fingerprint_sha256(payload)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_compatibility_policy_shape(self) -> None:
        policy = compatibility_policy()
        self.assertEqual(policy["latest_contract_version"], CONTRACT_VERSION_V2)
        self.assertIn(CONTRACT_VERSION_V1, policy["supported_contract_versions"])
        self.assertIn(CONTRACT_VERSION_V2, policy["supported_contract_versions"])
        self.assertIn(CONTRACT_VERSION_V2, policy["supported_validation_targets"])
        self.assertIn("sector_feed_id", policy["required_top_level_fields"])
        self.assertIn("feed_episode_id", policy["required_episode_fields"])
        self.assertIn("context.deck_id", policy["v2_required_top_level_fields"])
        self.assertEqual(policy["v2_context_aliases"]["stream_id"], "deck_id")
        self.assertEqual(VALIDATION_OUTPUT_VERSION, "bitpod_intake_handshake_validation_output.v1")


if __name__ == "__main__":
    unittest.main()
