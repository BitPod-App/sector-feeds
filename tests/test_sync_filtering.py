from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import bitpod.sync as sync_module
from bitpod.sync import (
    _choose_best_source,
    _dedupe_cross_source_variants,
    _find_matching_youtube_episode,
    _is_live_like_youtube_episode,
    _normalized_episode_title,
    _status_basename,
    filter_episodes,
    get_feed_urls,
)


@dataclass
class DummyEpisode:
    guid: str
    title: str
    published_at: datetime
    source_url: str
    source_type: str = "unknown"
    feed_url: str = "https://example.com/feed.xml"


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

    def test_get_feed_urls_rss_preferred_skips_youtube_when_rss_exists(self) -> None:
        show = {
            "feeds": {
                "youtube": "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
                "rss": ["https://example.com/feed.xml"],
            }
        }
        self.assertEqual(get_feed_urls(show, feed_mode="rss_preferred"), ["https://example.com/feed.xml"])

    def test_get_feed_urls_rss_preferred_falls_back_to_youtube(self) -> None:
        show = {
            "feeds": {
                "youtube": "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
            }
        }
        self.assertEqual(
            get_feed_urls(show, feed_mode="rss_preferred"),
            ["https://www.youtube.com/feeds/videos.xml?channel_id=abc"],
        )

    def test_get_feed_urls_rss_only_excludes_youtube(self) -> None:
        show = {
            "feeds": {
                "youtube": "https://www.youtube.com/feeds/videos.xml?channel_id=abc",
                "rss": ["https://example.com/feed.xml"],
            }
        }
        self.assertEqual(get_feed_urls(show, feed_mode="rss_only"), ["https://example.com/feed.xml"])

    def test_choose_best_source_prefers_rss_audio_over_youtube(self) -> None:
        newer_youtube = DummyEpisode(
            guid="same",
            title="newer",
            published_at=datetime.now(timezone.utc),
            source_url="https://youtube.com/watch?v=x",
            source_type="youtube_video",
        )
        older_rss = DummyEpisode(
            guid="same",
            title="older",
            published_at=datetime.now(timezone.utc) - timedelta(days=1),
            source_url="https://podcast.example/ep1",
            source_type="rss_audio",
        )
        chosen = _choose_best_source(newer_youtube, older_rss)
        self.assertEqual(chosen.source_type, "rss_audio")

    def test_normalized_episode_title_ignores_punctuation(self) -> None:
        self.assertEqual(
            _normalized_episode_title("Oil, Bonds, and Bitcoin: The Rules Are That There Are No Rules"),
            "oil bonds and bitcoin the rules are that there are no rules",
        )

    def test_cross_source_dedupe_prefers_rss_when_title_and_date_match(self) -> None:
        published = datetime(2026, 3, 1, tzinfo=timezone.utc)
        rss = DummyEpisode(
            guid="rss-guid",
            title="Oil, Bonds, and Bitcoin: The Rules Are That There Are No Rules",
            published_at=published,
            source_url="https://podcast.example/oil-bonds",
            source_type="rss_audio",
        )
        youtube = DummyEpisode(
            guid="yt-guid",
            title="Oil, Bonds, and Bitcoin: The Rules Are That There Are No Rules",
            published_at=published + timedelta(hours=2),
            source_url="https://youtube.com/watch?v=abc",
            source_type="youtube_video",
        )
        deduped = _dedupe_cross_source_variants([rss, youtube])
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].source_type, "rss_audio")

    def test_cross_source_dedupe_does_not_merge_far_apart_reposts(self) -> None:
        rss = DummyEpisode(
            guid="rss-guid",
            title="What Is Money? (And Why Bitcoin Matters)",
            published_at=datetime(2025, 12, 30, tzinfo=timezone.utc),
            source_url="https://podcast.example/what-is-money",
            source_type="rss_audio",
        )
        youtube = DummyEpisode(
            guid="yt-guid",
            title="What Is Money? (And Why Bitcoin Matters)",
            published_at=datetime(2026, 1, 6, tzinfo=timezone.utc),
            source_url="https://youtube.com/watch?v=def",
            source_type="youtube_video",
        )
        deduped = _dedupe_cross_source_variants([rss, youtube])
        self.assertEqual(len(deduped), 2)

    def test_find_matching_youtube_episode_prefers_matching_youtube_variant(self) -> None:
        published = datetime(2026, 3, 1, tzinfo=timezone.utc)
        rss = DummyEpisode(
            guid="rss-guid",
            title="Mail Bag Monday: Japan, AI, and Bitcoin",
            published_at=published,
            source_url="https://podcast.example/mailbag",
            source_type="rss_audio",
        )
        youtube = DummyEpisode(
            guid="yt-guid",
            title="Mail Bag Monday: Japan, AI, and Bitcoin",
            published_at=published + timedelta(hours=1),
            source_url="https://youtube.com/watch?v=mailbag",
            source_type="youtube_video",
        )
        self.assertEqual(_find_matching_youtube_episode(rss, [rss, youtube]), youtube)

    def test_status_basename_uses_stable_pointer_stem(self) -> None:
        show = {"show_key": "demo_show", "stable_pointer": "demo_latest.md"}
        self.assertEqual(_status_basename(show), "demo_latest_status")

    def test_sync_dry_run_defers_recent_youtube_but_keeps_recent_rss(self) -> None:
        now = datetime.now(timezone.utc)
        episodes = [
            DummyEpisode(
                guid="yt_recent",
                title="yt recent",
                published_at=now - timedelta(minutes=30),
                source_url="https://youtube.com/watch?v=recent",
                source_type="youtube_video",
                feed_url="https://youtube.com/feed",
            ),
            DummyEpisode(
                guid="yt_old",
                title="yt old",
                published_at=now - timedelta(hours=4),
                source_url="https://youtube.com/watch?v=old",
                source_type="youtube_video",
                feed_url="https://youtube.com/feed",
            ),
            DummyEpisode(
                guid="rss_recent",
                title="rss recent",
                published_at=now - timedelta(minutes=10),
                source_url="https://podcast.example/ep",
                source_type="rss_audio",
                feed_url="https://podcast.example/feed.xml",
            ),
        ]

        from unittest.mock import patch

        show = {
            "show_key": "demo_show",
            "feeds": {"youtube": "https://youtube.com/feed", "rss": ["https://podcast.example/feed.xml"]},
            "stable_pointer": "demo_latest.md",
        }
        with patch("bitpod.feeds.parse_feed", side_effect=[episodes[:2], episodes[2:]]), patch.object(
            sync_module, "load_processed", return_value={"episodes": {}}
        ):
            stats = sync_module.sync_show(
                show=show,
                max_episodes=5,
                dry_run=True,
                as_of_utc=now,
                min_episode_age_minutes=180,
            )

        selected_titles = [item["title"] for item in stats["would_process"]]
        self.assertIn("yt old", selected_titles)
        self.assertIn("rss recent", selected_titles)
        self.assertNotIn("yt recent", selected_titles)
        self.assertEqual(stats["deferred_recent_youtube"], 1)

    def test_is_live_like_youtube_episode(self) -> None:
        yt_live = DummyEpisode(
            guid="1",
            title="LIVE: market update",
            published_at=datetime.now(timezone.utc),
            source_url="https://youtube.com/watch?v=1",
            source_type="youtube_video",
        )
        yt_normal = DummyEpisode(
            guid="2",
            title="Weekly recap",
            published_at=datetime.now(timezone.utc),
            source_url="https://youtube.com/watch?v=2",
            source_type="youtube_video",
        )
        rss_live_word = DummyEpisode(
            guid="3",
            title="Live from conference",
            published_at=datetime.now(timezone.utc),
            source_url="https://podcast.example/3",
            source_type="rss_audio",
        )
        self.assertTrue(_is_live_like_youtube_episode(yt_live))
        self.assertFalse(_is_live_like_youtube_episode(yt_normal))
        self.assertFalse(_is_live_like_youtube_episode(rss_live_word))

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
            show = {"show_key": "jack_mallers_show", "stable_pointer": "jack_mallers.md"}

            original_root = sync_module.TRANSCRIPTS_ROOT
            sync_module.TRANSCRIPTS_ROOT = temp_root / "transcripts"
            try:
                sync_module._refresh_stable_pointer(show, index)
            finally:
                sync_module.TRANSCRIPTS_ROOT = original_root

            pointer = temp_root / "transcripts" / "jack_mallers_show" / "jack_mallers.md"
            self.assertTrue(pointer.exists())
            self.assertEqual(pointer.read_text(encoding="utf-8"), "new transcript\n")


if __name__ == "__main__":
    unittest.main()
