from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.audio import _captions_are_bad, _parse_vtt_cues, _stitch_cues_dedup


class CaptionProcessingTests(unittest.TestCase):
    def test_parse_vtt_cues_strips_metadata(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:03.000 align:start position:0%
<v Speaker>We are going to talk about bitcoin</v>

00:00:03.000 --> 00:00:06.000
about bitcoin and liquidity.
"""
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.vtt"
            path.write_text(vtt, encoding="utf-8")
            cues = _parse_vtt_cues(path)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text, "We are going to talk about bitcoin")
        self.assertEqual(cues[1].text, "about bitcoin and liquidity.")

    def test_stitch_removes_overlap(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.vtt"
            path.write_text(
                """WEBVTT

00:00:00.000 --> 00:00:03.000
we are going to talk about bitcoin

00:00:03.000 --> 00:00:06.000
talk about bitcoin and liquidity
""",
                encoding="utf-8",
            )
            cues = _parse_vtt_cues(path)
        stitched = _stitch_cues_dedup(cues)
        self.assertEqual(stitched, "we are going to talk about bitcoin and liquidity")

    def test_quality_gate_detects_repetitive_transcript(self) -> None:
        repetitive = " ".join(["bitcoin is money"] * 600)
        bad, metrics = _captions_are_bad(repetitive, cue_count=2500, min_words=120)
        self.assertTrue(bad)
        self.assertGreater(metrics["repetition_ratio_5gram"], 0.10)


if __name__ == "__main__":
    unittest.main()
