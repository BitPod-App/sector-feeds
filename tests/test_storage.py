from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bitpod.storage import slugify, transcript_path


class StorageTests(unittest.TestCase):
    def test_slugify_basic(self) -> None:
        self.assertEqual(slugify("Hello, World! Episode #1"), "hello-world-episode-1")

    def test_transcript_path_layout(self) -> None:
        dt = datetime(2025, 1, 2, tzinfo=timezone.utc)
        path = transcript_path("jack_mallers_show", dt, "Big Interview")
        self.assertTrue(path.as_posix().endswith("transcripts/jack_mallers_show/2025/2025-01-02__big-interview.md"))


if __name__ == "__main__":
    unittest.main()
