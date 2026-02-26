from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.storage import (
    write_public_permalink_artifacts,
    slugify,
    status_paths,
    transcript_path,
    write_gpt_review_request,
    write_output_artifacts,
    write_run_status_artifacts,
)


class StorageTests(unittest.TestCase):
    def test_slugify_basic(self) -> None:
        self.assertEqual(slugify("Hello, World! Episode #1"), "hello-world-episode-1")

    def test_transcript_path_layout(self) -> None:
        dt = datetime(2025, 1, 2, tzinfo=timezone.utc)
        path = transcript_path("jack_mallers_show", dt, "Big Interview")
        self.assertTrue(path.as_posix().endswith("transcripts/jack_mallers_show/2025/2025-01-02__big-interview.md"))

    def test_write_output_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            transcript_file = transcript_path(
                "jack_mallers_show",
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                "Big Interview",
                root=Path(tmp),
            )
            transcript_file.parent.mkdir(parents=True, exist_ok=True)
            transcript_file.write_text("placeholder", encoding="utf-8")
            plain, segments = write_output_artifacts(
                transcript_file=transcript_file,
                transcript_text="Hello world",
                segments=[{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_0", "text": "Hello"}],
                metadata={"source_platform": "youtube", "transcription_method": "youtube_captions_stitched"},
            )
            self.assertTrue(plain.exists())
            self.assertTrue(segments.exists())

    def test_write_run_status_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            from bitpod import storage as storage_module

            original_root = storage_module.TRANSCRIPTS_ROOT
            storage_module.TRANSCRIPTS_ROOT = Path(tmp) / "transcripts"
            try:
                payload = {
                    "show_key": "jack_mallers_show",
                    "run_id": "20260225T190000Z",
                    "run_status": "failed",
                    "included_in_pointer": False,
                    "failure_stage": "transcription",
                    "failure_reason": "quota exceeded",
                }
                json_path, md_path = write_run_status_artifacts(show_key="jack_mallers_show", payload=payload)
                expected_json, expected_md = status_paths("jack_mallers_show")
            finally:
                storage_module.TRANSCRIPTS_ROOT = original_root

            self.assertEqual(json_path, expected_json)
            self.assertEqual(md_path, expected_md)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

    def test_write_gpt_review_request(self) -> None:
        with TemporaryDirectory() as tmp:
            from bitpod import storage as storage_module

            original_root = storage_module.TRANSCRIPTS_ROOT
            storage_module.TRANSCRIPTS_ROOT = Path(tmp) / "transcripts"
            try:
                payload = {
                    "show_key": "jack_mallers_show",
                    "run_id": "20260225T190000Z",
                    "run_status": "failed",
                    "failure_stage": "transcription",
                    "failure_reason": "quota exceeded",
                    "pointer_path": "transcripts/jack_mallers_show/jack_mallers.md",
                }
                review_path = write_gpt_review_request(
                    show_key="jack_mallers_show",
                    payload=payload,
                    status_basename="jack_mallers_status",
                )
            finally:
                storage_module.TRANSCRIPTS_ROOT = original_root

            self.assertTrue(review_path.exists())

    def test_write_public_permalink_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            from unittest.mock import patch
            from bitpod import storage as storage_module

            root = Path(tmp)
            pointer = root / "transcripts" / "jack_mallers_show" / "jack_mallers.md"
            pointer.parent.mkdir(parents=True, exist_ok=True)
            pointer.write_text("# Latest\n\nTranscript body.\n", encoding="utf-8")
            transcript_file = root / "transcripts" / "jack_mallers_show" / "2026" / "2026-02-24__episode.md"
            transcript_file.parent.mkdir(parents=True, exist_ok=True)
            transcript_file.write_text("# Episode\n\nTranscript body.\n", encoding="utf-8")
            index_path = root / "index" / "processed.json"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                json.dumps(
                    {
                        "episodes": {
                            "jack_mallers_show::ok-guid": {
                                "status": "ok",
                                "published_at": "2026-02-24T09:49:52+00:00",
                                "source_url": "https://example.com/ok",
                                "transcript_path": str(transcript_file),
                            },
                            "jack_mallers_show::failed-guid": {
                                "status": "failed",
                                "published_at": "2026-02-25T09:49:52+00:00",
                                "source_url": "https://example.com/failed",
                                "stage": "transcription",
                                "reason": "quota",
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            original_root = storage_module.ROOT
            original_transcripts_root = storage_module.TRANSCRIPTS_ROOT
            storage_module.ROOT = root
            storage_module.TRANSCRIPTS_ROOT = root / "transcripts"
            try:
                payload = {
                    "run_id": "20260225T190000Z",
                    "run_status": "ok",
                    "included_in_pointer": True,
                    "latest_episode_published_at_utc": "2026-02-25T19:00:00+00:00",
                    "pointer_updated_at_utc": "2026-02-25T19:05:00+00:00",
                    "pointer_path": str(pointer),
                }
                with patch.dict("os.environ", {"BITPOD_PUBLIC_ID_SALT": "test-salt"}, clear=False):
                    first = write_public_permalink_artifacts(show_key="jack_mallers_show", status_payload=payload)
                    second = write_public_permalink_artifacts(show_key="jack_mallers_show", status_payload=payload)
            finally:
                storage_module.ROOT = original_root
                storage_module.TRANSCRIPTS_ROOT = original_transcripts_root

            self.assertEqual(first["public_permalink_id"], second["public_permalink_id"])
            self.assertNotIn("jack_mallers_show", first["public_permalink_latest_path"])

            latest_path = Path(first["public_permalink_latest_path"])
            status_path = Path(first["public_permalink_status_path"])
            manifest_path = Path(first["public_permalink_manifest_path"])
            self.assertTrue(latest_path.exists())
            self.assertTrue(status_path.exists())
            self.assertTrue(manifest_path.exists())

            latest_text = latest_path.read_text(encoding="utf-8")
            self.assertIn("robots: noindex, nofollow, noarchive", latest_text)
            self.assertIn("Processed Episodes (oldest to newest)", latest_text)
            self.assertIn("episodes/2026-02-24__episode.md", latest_text)
            self.assertIn("Unprocessed Episodes", latest_text)
            self.assertIn("processing_order: `oldest_to_newest`", latest_text)

            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(status_payload["run_status"], "ok")
            self.assertEqual(status_payload["robots"], "noindex, nofollow, noarchive")
            self.assertEqual(status_payload["processed_count"], 1)
            self.assertEqual(status_payload["processed_total_count"], 1)
            self.assertEqual(status_payload["unprocessed_count"], 1)
            self.assertEqual(status_payload["processing_order"], "oldest_to_newest")
            self.assertEqual(status_payload["contract_version"], "public_permalink_status.v1")
            self.assertEqual(status_payload["processor_mode"], "batch_oldest_to_newest")
            self.assertEqual(status_payload["processor_queue_count"], 1)
            self.assertEqual(status_payload["min_episodes_window"], 5)
            self.assertEqual(status_payload["max_episodes_window"], 10)
            self.assertEqual(status_payload["target_total_minutes"], 180.0)
            self.assertEqual(status_payload["processed_episodes"][0]["guid"], "ok-guid")
            self.assertEqual(status_payload["unprocessed_episodes"][0]["guid"], "failed-guid")

            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("jack_mallers_show", manifest_payload["shows"])


if __name__ == "__main__":
    unittest.main()
