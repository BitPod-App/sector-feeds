from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.storage import (
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


if __name__ == "__main__":
    unittest.main()
