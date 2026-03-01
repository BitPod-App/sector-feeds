from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.deck_state import is_consumed, load_deck_state, mark_consumed


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


if __name__ == "__main__":
    unittest.main()
