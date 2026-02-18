from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bitpod.sync import filter_episodes, get_feed_urls


@dataclass
class DummyEpisode:
    guid: str
    title: str
    published_at: datetime
    source_url: str


def _ep(title: str, days_ago: int) -> DummyEpisode:
    published = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return DummyEpisode(guid=title, title=title, published_at=published, source_url=f"https://example.com/{title}")


class SyncFilteringTests(unittest.TestCase):
    def test_filter_episodes_max_episodes_newest_first(self) -> None:
        episodes = [_ep("old", 20), _ep("new", 1), _ep("middle", 5)]
        selected = filter_episodes(episodes, max_episodes=2)
        self.assertEqual([ep.title for ep in selected], ["new", "middle"])

    def test_filter_episodes_since_days(self) -> None:
        episodes = [_ep("in-range", 2), _ep("too-old", 10)]
        selected = filter_episodes(episodes, max_episodes=5, since_days=7)
        self.assertEqual([ep.title for ep in selected], ["in-range"])

    def test_get_feed_urls_supports_youtube_and_rss(self) -> None:
        show = {
            "feeds": {
                "youtube": "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
                "rss": ["https://example.com/feed.xml", "https://example.com/feed.xml"],
            }
        }
        self.assertEqual(
            get_feed_urls(show),
            [
                "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
                "https://example.com/feed.xml",
            ],
        )


if __name__ == "__main__":
    unittest.main()
