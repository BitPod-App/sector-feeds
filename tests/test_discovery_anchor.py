from __future__ import annotations

import unittest

from bitpod.discovery import discover_show_feeds


class DiscoveryAnchorTests(unittest.TestCase):
    def test_discover_show_feeds_uses_explicit_anchor_show_id(self) -> None:
        show = {
            "show_key": "jack_mallers_show",
            "anchor_show_id": "e29097f4",
            "feeds": {"rss": []},
        }
        feeds = discover_show_feeds(show)
        self.assertIn("rss", feeds)
        self.assertEqual(feeds["rss"][0], "https://anchor.fm/s/e29097f4/podcast/rss")

    def test_discover_show_feeds_infers_anchor_from_website_url(self) -> None:
        show = {
            "show_key": "jack_mallers_show",
            "website_url": "https://anchor.fm/s/e29097f4",
            "feeds": {"rss": []},
        }
        feeds = discover_show_feeds(show)
        self.assertEqual(feeds["rss"][0], "https://anchor.fm/s/e29097f4/podcast/rss")


if __name__ == "__main__":
    unittest.main()
