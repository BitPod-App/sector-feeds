from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.deck_state import (
    is_consumed,
    is_consumed_for_stream,
    load_deck_state,
    load_stream_state,
    mark_consumed,
    mark_stream_consumed,
)


class DeckStateTests(unittest.TestCase):
    def test_mark_and_check_consumed(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck_state.json"
            self.assertFalse(is_consumed("deck-alpha", "jack_mallers_show", "ep-1", path=path))
            mark_consumed("deck-alpha", "jack_mallers_show", "ep-1", path=path)
            self.assertTrue(is_consumed("deck-alpha", "jack_mallers_show", "ep-1", path=path))
            state = load_deck_state(path=path)
            self.assertIn("consumed_feed_episode_ids", state["decks"]["deck-alpha"]["jack_mallers_show"])

    def test_load_empty_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            state = load_deck_state(path=path)
            self.assertEqual(state["version"], 1)
            self.assertIn("decks", state)

    def test_stream_aliases_delegate_to_legacy_storage(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "deck_state.json"
            self.assertFalse(is_consumed_for_stream("stream-alpha", "jack_mallers_show", "ep-1", path=path))
            mark_stream_consumed("stream-alpha", "jack_mallers_show", "ep-1", path=path)
            self.assertTrue(is_consumed_for_stream("stream-alpha", "jack_mallers_show", "ep-1", path=path))
            state = load_stream_state(path=path)
            self.assertIn("stream-alpha", state["decks"])


if __name__ == "__main__":
    unittest.main()
