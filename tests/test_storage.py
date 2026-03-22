from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.storage import (
    _landing_page_html,
    write_public_permalink_artifacts,
    slugify,
    status_paths,
    transcript_path,
    write_gpt_review_request,
    write_output_artifacts,
    write_run_status_artifacts,
)


class StorageTests(unittest.TestCase):
    def test_landing_page_html_uses_distinct_state_copy(self) -> None:
        base_payload = {
            "public_id": "opaque123",
            "run_id": "20260317T051151Z",
            "run_status": "ok",
            "new_episode_detected": True,
            "included_in_pointer": True,
            "episode_title": "Big Interview",
            "published_at_utc": "2026-03-16T23:42:10+00:00",
            "transcript_provenance": "youtube_auto_captions",
            "transcript_quality_state": "usable",
            "transcript_degraded": False,
            "source_mode": "captions",
            "transcript_source_type": "youtube_video",
            "transcript_source_url": "https://example.com/video",
            "public_bundle_complete": True,
            "public_bundle_missing": [],
            "public_bundle_verification_mode": "public_http",
            "public_bundle_verified_at_utc": "2026-03-17T07:25:05Z",
            "public_bundle_readability": {
                "status.json": {"readable": True, "verified_via": "public_http"},
                "intake.md": {"readable": True, "verified_via": "public_http"},
                "transcript.md": {"readable": True, "verified_via": "public_http"},
                "discovery.json": {"readable": True, "verified_via": "public_http"},
            },
        }

        usable_html = _landing_page_html(permalink_id="opaque123", base_url="https://example.com", public_status=base_payload)
        self.assertIn("usable transcript", usable_html)
        self.assertIn("low-weight context", usable_html)
        self.assertIn("Speak transcript", usable_html)
        self.assertIn("speechSynthesis", usable_html)
        self.assertIn("Pause</button>", usable_html)
        self.assertIn("https://example.com/opaque123/transcript.md", usable_html)

        degraded_payload = dict(base_payload, transcript_quality_state="degraded", transcript_degraded=True)
        degraded_html = _landing_page_html(
            permalink_id="opaque123",
            base_url="https://example.com",
            public_status=degraded_payload,
        )
        self.assertIn("low-confidence context", degraded_html)
        self.assertIn("Transcript quality state: degraded.", degraded_html)

        failed_payload = dict(
            base_payload,
            run_status="failed",
            included_in_pointer=False,
            transcript_quality_state="failed",
            failure_stage="transcription",
            failure_reason="quota exceeded",
        )
        failed_html = _landing_page_html(
            permalink_id="opaque123",
            base_url="https://example.com",
            public_status=failed_payload,
        )
        self.assertIn("intake failed", failed_html)
        self.assertIn("Failure stage: transcription.", failed_html)
        self.assertIn("Failure reason: quota exceeded.", failed_html)

        no_new_payload = dict(
            base_payload,
            new_episode_detected=False,
            included_in_pointer=False,
            transcript_quality_state="no-new-episode",
        )
        no_new_html = _landing_page_html(
            permalink_id="opaque123",
            base_url="https://example.com",
            public_status=no_new_payload,
        )
        self.assertIn("No new episode was detected on this run.", no_new_html)
        self.assertIn("no-new-episode", no_new_html)

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
                metadata={
                    "source_platform": "youtube",
                    "source_episode_id": "yt:video:abc123",
                    "transcription_method": "youtube_captions_stitched",
                },
            )
            self.assertTrue(plain.exists())
            self.assertTrue(segments.exists())
            text = plain.read_text(encoding="utf-8")
            self.assertIn('source_episode_id: "yt:video:abc123"', text)
            self.assertNotIn('source_id: "', text)

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
                    "governance": {
                        "provenance_tuple": {"origin_actor": "CJ", "authority_state": "CJ_OVERRIDE"},
                        "spec_lock": {"expansion_gate": "BLOCKED"},
                        "override_guard": {
                            "required": True,
                            "complete": False,
                            "missing_fields": ["conflict_note"],
                        },
                    },
                }
                json_path, md_path = write_run_status_artifacts(show_key="jack_mallers_show", payload=payload)
                expected_json, expected_md = status_paths("jack_mallers_show")
            finally:
                storage_module.TRANSCRIPTS_ROOT = original_root

            self.assertEqual(json_path, expected_json)
            self.assertEqual(md_path, expected_md)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn("## Governance", md_text)
            self.assertIn("origin_actor: `CJ`", md_text)
            self.assertIn("authority_state: `CJ_OVERRIDE`", md_text)

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
                    "new_episode_detected": True,
                    "included_in_pointer": False,
                    "episode_title": "Big Interview",
                    "episode_guid": "ep-1",
                    "episode_url": "https://example.com/ep-1",
                    "published_at_utc": "2026-02-25T19:00:00+00:00",
                    "transcript_provenance": "failed",
                    "source_mode": None,
                    "transcript_quality_state": "failed",
                    "transcript_degraded": False,
                    "failure_stage": "transcription",
                    "failure_reason": "quota exceeded",
                    "pointer_path": "transcripts/jack_mallers_show/jack_mallers.md",
                    "public_permalink_status_url": "https://permalinks.bitpod.app/abc123/status.json",
                    "public_permalink_intake_url": "https://permalinks.bitpod.app/abc123/intake.md",
                    "public_permalink_transcript_url": "https://permalinks.bitpod.app/abc123/transcript.md",
                    "public_permalink_discovery_url": "https://permalinks.bitpod.app/abc123/discovery.json",
                }
                review_path = write_gpt_review_request(
                    show_key="jack_mallers_show",
                    payload=payload,
                    status_basename="jack_mallers_status",
                )
            finally:
                storage_module.TRANSCRIPTS_ROOT = original_root

            self.assertTrue(review_path.exists())
            review_text = review_path.read_text(encoding="utf-8")
            self.assertIn("Use the public permalink bundle as the canonical input surface", review_text)
            self.assertIn("status_json_url: `https://permalinks.bitpod.app/abc123/status.json`", review_text)
            self.assertIn("### 6. Basic BTC output report", review_text)
            self.assertIn("transcript_provenance: `failed`", review_text)

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
                    "new_episode_detected": True,
                    "included_in_pointer": True,
                    "sector_tags": ["Bitcoiners"],
                    "episode_title": "Big Interview",
                    "episode_guid": "ok-guid",
                    "episode_url": "https://example.com/ok",
                    "published_at_utc": "2026-02-25T19:00:00+00:00",
                    "transcript_provenance": "youtube_auto_captions",
                    "source_mode": "captions",
                    "transcript_quality_state": "usable",
                    "transcript_degraded": False,
                    "failure_stage": None,
                    "failure_reason": None,
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
            transcript_path = Path(first["public_permalink_transcript_path"])
            intake_path = Path(first["public_permalink_intake_path"])
            status_path = Path(first["public_permalink_status_path"])
            discovery_path = Path(first["public_permalink_discovery_path"])
            landing_path = Path(first["public_permalink_landing_path"])
            manifest_path = Path(first["public_permalink_manifest_path"])
            self.assertTrue(latest_path.exists())
            self.assertTrue(transcript_path.exists())
            self.assertTrue(intake_path.exists())
            self.assertTrue(status_path.exists())
            self.assertTrue(discovery_path.exists())
            self.assertTrue(landing_path.exists())
            self.assertTrue(manifest_path.exists())

            latest_text = latest_path.read_text(encoding="utf-8")
            self.assertIn("robots: noindex, nofollow, noarchive", latest_text)
            self.assertIn("Processed Episodes (oldest to newest)", latest_text)
            self.assertIn("episodes/2026-02-24__episode.md", latest_text)
            self.assertIn("Unprocessed Episodes", latest_text)
            self.assertIn("processing_order: `oldest_to_newest`", latest_text)
            intake_text = intake_path.read_text(encoding="utf-8")
            self.assertIn("# Transcript Intake", intake_text)
            self.assertIn("[discovery.json](discovery.json)", intake_text)
            self.assertIn("[transcript.md](transcript.md)", intake_text)
            self.assertIn("new_episode_detected: `True`", intake_text)
            self.assertIn("episode_title: `Big Interview`", intake_text)
            self.assertIn("transcript_provenance: `youtube_auto_captions`", intake_text)
            transcript_text = transcript_path.read_text(encoding="utf-8")
            self.assertIn("# Episode", transcript_text)
            landing_text = landing_path.read_text(encoding="utf-8")
            self.assertIn("BitPod Permalink Bundle", landing_text)
            self.assertIn('id="bitpod-run-contract"', landing_text)
            self.assertIn("Canonical evidence", landing_text)
            self.assertIn("local_fs_only", landing_text)
            self.assertIn(
                f'href="https://permalinks.bitpod.app/{first["public_permalink_id"]}/status.json"',
                landing_text,
            )

            status_payload = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(status_payload["run_status"], "ok")
            self.assertTrue(status_payload["new_episode_detected"])
            self.assertEqual(status_payload["robots"], "noindex, nofollow, noarchive")
            self.assertEqual(status_payload["sector_tags"], ["Bitcoiners"])
            self.assertEqual(status_payload["format_tags"], [])
            self.assertEqual(status_payload["source_platform_tags"], [])
            self.assertEqual(status_payload["sector_feed_id"], "jack_mallers_show")
            self.assertEqual(status_payload["show_key"], "jack_mallers_show")
            self.assertTrue(status_payload["series_is_feed_unit"])
            self.assertEqual(status_payload["feed_unit_type"], "series_or_playlist_or_feed")
            self.assertEqual(status_payload["landing_path"], "index.html")
            self.assertEqual(status_payload["intake_path"], "intake.md")
            self.assertEqual(status_payload["transcript_path"], "transcript.md")
            self.assertEqual(status_payload["episode_title"], "Big Interview")
            self.assertEqual(status_payload["episode_guid"], "ok-guid")
            self.assertEqual(status_payload["episode_url"], "https://example.com/ok")
            self.assertEqual(status_payload["published_at_utc"], "2026-02-25T19:00:00+00:00")
            self.assertEqual(status_payload["transcript_provenance"], "youtube_auto_captions")
            self.assertEqual(status_payload["source_mode"], "captions")
            self.assertEqual(status_payload["transcript_quality_state"], "usable")
            self.assertFalse(status_payload["transcript_degraded"])
            self.assertFalse(status_payload["public_bundle_complete"])
            self.assertEqual(status_payload["public_bundle_missing"], [])
            self.assertIsNone(status_payload["public_bundle_readability"]["status.json"]["readable"])
            self.assertEqual(status_payload["public_bundle_readability"]["status.json"]["verified_via"], "local_fs")
            self.assertTrue(status_payload["public_bundle_readability"]["status.json"]["local_exists"])
            self.assertEqual(status_payload["public_bundle_verification_mode"], "local_fs_only")
            self.assertIsNone(status_payload["public_bundle_verified_at_utc"])
            self.assertEqual(
                status_payload["public_bundle_readability"]["intake.md"]["url"],
                f"https://permalinks.bitpod.app/{first['public_permalink_id']}/intake.md",
            )
            self.assertEqual(status_payload["processed_count"], 1)
            self.assertEqual(status_payload["processed_total_count"], 1)
            self.assertEqual(status_payload["unprocessed_count"], 1)
            self.assertEqual(status_payload["processing_order"], "oldest_to_newest")
            self.assertEqual(status_payload["window_profile"], "short_transcript_profile")
            self.assertEqual(status_payload["contract_version"], "public_permalink_status.v1")
            self.assertEqual(status_payload["processor_mode"], "batch_oldest_to_newest")
            self.assertEqual(status_payload["processor_queue_count"], 1)
            self.assertEqual(status_payload["min_episodes_window"], 5)
            self.assertEqual(status_payload["max_episodes_window"], 10)
            self.assertEqual(status_payload["long_transcript_threshold_chars"], 18000)
            self.assertEqual(status_payload["target_total_minutes"], 180.0)
            self.assertEqual(status_payload["processed_episodes"][0]["guid"], "ok-guid")
            self.assertEqual(status_payload["processed_episodes"][0]["feed_episode_id"], "ok-guid")
            self.assertTrue(status_payload["processed_episodes"][0]["canonical_episode_id"])
            self.assertEqual(
                status_payload["processed_episodes"][0]["canonical_video_url"],
                "https://example.com/ok",
            )
            self.assertEqual(
                status_payload["processed_episodes"][0]["playlist_context_url"],
                "https://example.com/ok",
            )
            self.assertEqual(status_payload["unprocessed_episodes"][0]["guid"], "failed-guid")
            self.assertIn("processed_episode_ids", status_payload)
            self.assertIn("unprocessed_episode_ids", status_payload)

            discovery_payload = json.loads(discovery_path.read_text(encoding="utf-8"))
            self.assertEqual(discovery_payload["contract_version"], "public_permalink_discovery.v1")
            self.assertEqual(discovery_payload["sector_feed_id"], "jack_mallers_show")
            self.assertTrue(discovery_payload["series_is_feed_unit"])
            self.assertEqual(discovery_payload["feed_unit_type"], "series_or_playlist_or_feed")
            self.assertEqual(discovery_payload["entrypoints"]["landing_html"], "index.html")
            self.assertEqual(discovery_payload["entrypoints"]["intake_md"], "intake.md")
            self.assertEqual(discovery_payload["entrypoints"]["transcript_md"], "transcript.md")
            self.assertEqual(discovery_payload["entrypoints"]["latest_md"], "latest.md")
            self.assertIn("episodes/2026-02-24__episode.md", discovery_payload["published_episode_files"])
            self.assertIn("ok-guid", discovery_payload["processed_episode_ids"])

            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("jack_mallers_show", manifest_payload["shows"])
            self.assertEqual(manifest_payload["shows"]["jack_mallers_show"]["sector_tags"], ["Bitcoiners"])
            self.assertEqual(manifest_payload["shows"]["jack_mallers_show"]["format_tags"], [])
            self.assertEqual(manifest_payload["shows"]["jack_mallers_show"]["source_platform_tags"], [])
            self.assertTrue(manifest_payload["shows"]["jack_mallers_show"]["series_is_feed_unit"])
            self.assertIn("landing_html_path", manifest_payload["shows"]["jack_mallers_show"])
            self.assertIn("intake_md_path", manifest_payload["shows"]["jack_mallers_show"])
            self.assertEqual(
                first["public_permalink_landing_url"],
                f"https://permalinks.bitpod.app/{first['public_permalink_id']}",
            )
            self.assertEqual(
                first["public_permalink_transcript_url"],
                f"https://permalinks.bitpod.app/{first['public_permalink_id']}/transcript.md",
            )
            self.assertEqual(
                first["public_permalink_status_url"],
                f"https://permalinks.bitpod.app/{first['public_permalink_id']}/status.json",
            )


if __name__ == "__main__":
    unittest.main()
