from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import bitpod.sync as sync_module


@dataclass
class DummyEpisode:
    guid: str
    title: str
    published_at: datetime
    source_url: str
    feed_url: str
    source_type: str = "rss_audio"
    media_url: str | None = None


class WeeklyStatusTests(unittest.TestCase):
    def test_status_written_on_latest_failure_and_pointer_unchanged(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            transcripts_root = root / "transcripts"
            show_dir = transcripts_root / "jack_mallers_show"
            show_dir.mkdir(parents=True, exist_ok=True)
            pointer = show_dir / "jack_mallers.md"
            pointer.write_text("existing pointer\n", encoding="utf-8")

            episode = DummyEpisode(
                guid="ep1",
                title="Episode 1",
                published_at=datetime(2026, 2, 24, tzinfo=timezone.utc),
                source_url="https://example.com/ep1",
                feed_url="https://example.com/feed.xml",
            )

            original_root = sync_module.ROOT
            original_transcripts_root = sync_module.TRANSCRIPTS_ROOT
            from bitpod import storage as storage_module

            original_storage_root = storage_module.TRANSCRIPTS_ROOT
            original_parse_feed = None
            original_process_episode = sync_module._process_episode
            original_load_processed = sync_module.load_processed
            original_save_processed = sync_module.save_processed

            try:
                sync_module.ROOT = root
                sync_module.TRANSCRIPTS_ROOT = transcripts_root
                storage_module.TRANSCRIPTS_ROOT = transcripts_root

                import bitpod.feeds as feeds_module

                original_parse_feed = feeds_module.parse_feed
                feeds_module.parse_feed = lambda _: [episode]

                sync_module.load_processed = lambda: {"episodes": {}}
                sync_module.save_processed = lambda _: None

                def _fail_process_episode(**kwargs):
                    raise sync_module.ProcessingError(stage="transcription", reason="quota exceeded")

                sync_module._process_episode = _fail_process_episode

                stats = sync_module.sync_show(
                    show={
                        "show_key": "jack_mallers_show",
                        "stable_pointer": "jack_mallers.md",
                        "feeds": {"rss": ["https://example.com/feed.xml"]},
                    },
                    max_episodes=1,
                )
            finally:
                sync_module.ROOT = original_root
                sync_module.TRANSCRIPTS_ROOT = original_transcripts_root
                storage_module.TRANSCRIPTS_ROOT = original_storage_root
                sync_module._process_episode = original_process_episode
                sync_module.load_processed = original_load_processed
                sync_module.save_processed = original_save_processed
                if original_parse_feed is not None:
                    feeds_module.parse_feed = original_parse_feed

            self.assertEqual(stats["run_status"], "failed")
            self.assertFalse(stats["latest_included_in_pointer"])
            self.assertEqual(pointer.read_text(encoding="utf-8"), "existing pointer\n")

            status_json = show_dir / "jack_mallers_status.json"
            self.assertTrue(status_json.exists())
            payload = json.loads(status_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_status"], "failed")
            self.assertFalse(payload["included_in_pointer"])
            self.assertFalse(payload["ready_via_permalink"])
            self.assertEqual(payload["failure_stage"], "transcription")


if __name__ == "__main__":
    unittest.main()
