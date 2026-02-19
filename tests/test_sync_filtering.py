from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import bitpod.sync as sync_module
from bitpod.sync import _choose_best_source, filter_episodes, get_feed_urls


@dataclass
class DummyEpisode:
    guid: str
    title: str
    published_at: datetime
    source_url: str
    source_type: str = "unknown"
    feed_url: str = ""


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
                "https://example.com/feed.xml",
                "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
            ],
        )

    def test_choose_best_source_prefers_rss_audio_over_youtube(self) -> None:
        older = DummyEpisode(
            guid="same",
            title="Episode",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            source_url="https://youtube.com/watch?v=abc",
            source_type="youtube_video",
            feed_url="https://www.youtube.com/feeds/videos.xml?channel_id=abc",
        )
        newer = DummyEpisode(
            guid="same",
            title="Episode",
            published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            source_url="https://example.com/audio.mp3",
            source_type="rss_audio",
            feed_url="https://example.com/feed.xml",
        )
        chosen = _choose_best_source(older, newer)
        self.assertEqual(chosen.source_type, "rss_audio")

    def test_refresh_stable_pointer_uses_latest_successful_transcript(self) -> None:
        with TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            older = temp_root / "older.md"
            newer = temp_root / "newer.md"
            older.write_text("old transcript", encoding="utf-8")
            newer.write_text("new transcript", encoding="utf-8")

            index = {
                "episodes": {
                    "jack_mallers_show::old": {
                        "status": "ok",
                        "transcript_path": str(older),
                        "published_at": "2026-02-01T00:00:00+00:00",
                        "updated_at": "2026-02-01T01:00:00+00:00",
                    },
                    "jack_mallers_show::new": {
                        "status": "ok",
                        "transcript_path": str(newer),
                        "published_at": "2026-02-02T00:00:00+00:00",
                        "updated_at": "2026-02-02T01:00:00+00:00",
                    },
                }
            }
            show = {"show_key": "jack_mallers_show", "stable_pointer": "mallers_bitpod.md"}

            original_root = sync_module.TRANSCRIPTS_ROOT
            sync_module.TRANSCRIPTS_ROOT = temp_root / "transcripts"
            try:
                sync_module._refresh_stable_pointer(show, index)
            finally:
                sync_module.TRANSCRIPTS_ROOT = original_root

            pointer = temp_root / "transcripts" / "jack_mallers_show" / "mallers_bitpod.md"
            self.assertTrue(pointer.exists())
            self.assertEqual(pointer.read_text(encoding="utf-8"), "new transcript\n")


if __name__ == "__main__":
    unittest.main()
