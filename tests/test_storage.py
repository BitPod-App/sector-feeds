from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.storage import slugify, transcript_path, write_output_artifacts


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


if __name__ == "__main__":
    unittest.main()
