from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bitpod import ops as ops_module
from bitpod import track_reports as reports_module


class TrackReportTests(unittest.TestCase):
    def test_write_track_run_summary_uses_unique_paths_and_gpt_state(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_time = datetime(2026, 3, 11, 15, 4, 5, tzinfo=timezone.utc)
            fake_payload = {
                "latest_gpt_bitreport_path": str(root / "artifacts" / "gpt-bitreports" / "sample.md"),
                "latest_gpt_bitreport_coverage": "all",
                "shows": [
                    {
                        "show_key": "jack_mallers_show",
                        "latest_episode_guid": "ep-guid",
                        "latest_episode_title": "Episode X",
                        "latest_episode_published_at_utc": "2026-03-10T00:00:00+00:00",
                        "ready_via_permalink": True,
                        "run_status": "ok",
                        "run_id": "run-123",
                        "failure_stage": None,
                        "failure_reason": None,
                        "gpt_consumed": True,
                        "gpt_check_count": 2,
                        "latest_feedback_path": str(root / "artifacts" / "gpt-bitreports" / "sample.md"),
                        "latest_feedback_note": "auto-recorded",
                        "status_json": str(root / "transcripts" / "jack_mallers_show" / "jack_mallers_status.json"),
                        "status_md": str(root / "transcripts" / "jack_mallers_show" / "jack_mallers_status.md"),
                        "gpt_review_request": str(root / "transcripts" / "jack_mallers_show" / "jack_mallers_gpt_review_request.md"),
                        "latest_report_includes_show": True,
                    }
                ],
            }

            status_json = root / "transcripts" / "jack_mallers_show" / "jack_mallers_status.json"
            status_json.parent.mkdir(parents=True, exist_ok=True)
            status_json.write_text(
                json.dumps(
                    {
                        "source_platform": "rss_audio",
                        "source_url": "https://example.com/audio.mp3",
                        "source_episode_id": "src-1",
                        "canonical_episode_id": "canon-1",
                        "included_in_pointer": True,
                        "public_permalink_transcript_url": "https://example.com/transcript.md",
                        "public_permalink_status_url": "https://example.com/status.json",
                        "public_permalink_discovery_url": "https://example.com/discovery.json",
                        "public_permalink_status_path": str(root / "artifacts" / "public" / "permalinks" / "status.json"),
                        "public_permalink_transcript_path": str(root / "artifacts" / "public" / "permalinks" / "transcript.md"),
                        "public_permalink_intake_path": str(root / "artifacts" / "public" / "permalinks" / "intake.md"),
                        "public_permalink_discovery_path": str(root / "artifacts" / "public" / "permalinks" / "discovery.json"),
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(reports_module, "ROOT", root), patch.object(
                reports_module, "status_payload", lambda show_keys, as_of: fake_payload
            ), patch.object(reports_module, "_utc_now", lambda: run_time), patch.object(
                ops_module, "parse_as_of_local", lambda value=None: run_time
            ):
                md_path, json_path, summary = reports_module.write_track_run_summary(
                    "jack_mallers_show", "legacy_tuesday_track", "rss_preferred"
                )

            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("legacy_tuesday_track/jack_mallers_show", md_path.as_posix())
            self.assertTrue(md_path.name.endswith("__summary.md"))
            self.assertTrue(json_path.name.endswith("__status.json"))
            self.assertTrue(summary["success"])
            self.assertTrue(summary["gpt_consumed"])


if __name__ == "__main__":
    unittest.main()
