from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bitpod.core_intake_handshake import compatibility_policy, payload_fingerprint_sha256, pending_for_deck, validate_payload
from bitpod.deck_state import mark_consumed


class CoreIntakeHandshakeTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "contract_version": "bitregime_core_intake.v1",
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

    def test_validate_payload_ok(self) -> None:
        self.assertEqual(validate_payload(self._payload()), [])

    def test_validate_payload_missing_required_identity(self) -> None:
        payload = self._payload()
        payload["sector_feed_source_id"] = ""
        payload["episodes"][0]["processing_state"] = {}
        errors = validate_payload(payload)
        self.assertIn("missing:sector_feed_source_id", errors)
        self.assertIn("missing:episodes[0].processing_state.status", errors)

    def test_validate_payload_unsupported_contract(self) -> None:
        payload = self._payload()
        payload["contract_version"] = "bitregime_core_intake.v2"
        errors = validate_payload(payload)
        self.assertIn("unsupported_contract_version:bitregime_core_intake.v2", errors)

    def test_pending_for_deck_filters_consumed_and_terminal_state(self) -> None:
        payload = self._payload()
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            mark_consumed("deck-weekly-btc", "jack_mallers_show", "guid-1", path=deck_state_path)
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            self.assertEqual(pending, [])

    def test_pending_for_deck_keeps_non_terminal(self) -> None:
        payload = self._payload()
        payload["episodes"][1]["processing_state"]["status"] = "new"
        with tempfile.TemporaryDirectory() as tmp:
            deck_state_path = Path(tmp) / "deck_state.json"
            pending = pending_for_deck(payload, deck_id="deck-weekly-btc", deck_state_path=deck_state_path)
            ids = [row["feed_episode_id"] for row in pending]
            self.assertIn("guid-1", ids)
            self.assertIn("guid-2", ids)

    def test_payload_fingerprint_is_deterministic(self) -> None:
        payload = self._payload()
        first = payload_fingerprint_sha256(payload)
        second = payload_fingerprint_sha256(payload)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_compatibility_policy_shape(self) -> None:
        policy = compatibility_policy()
        self.assertEqual(policy["latest_contract_version"], "bitregime_core_intake.v1")
        self.assertIn("bitregime_core_intake.v1", policy["supported_contract_versions"])
        self.assertIn("sector_feed_id", policy["required_top_level_fields"])
        self.assertIn("feed_episode_id", policy["required_episode_fields"])


if __name__ == "__main__":
    unittest.main()
