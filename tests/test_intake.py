from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.intake import evaluate_intake_readiness


class IntakeReadinessTests(unittest.TestCase):
    def test_evaluate_intake_readiness_ok(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            show_root = root / "permalink"
            show_root.mkdir(parents=True, exist_ok=True)

            latest = show_root / "latest.md"
            intake = show_root / "intake.md"
            status = show_root / "status.json"
            discovery = show_root / "discovery.json"

            latest.write_text("# Transcript Index\n\n## Processed Episodes (oldest to newest)\n", encoding="utf-8")
            intake.write_text(
                "# Transcript Intake\n\n[transcript.md](transcript.md)\n[latest.md](latest.md)\n[status.json](status.json)\n[discovery.json](discovery.json)\n",
                encoding="utf-8",
            )
            status.write_text(
                json.dumps(
                    {
                        "contract_version": "public_permalink_status.v1",
                        "transcript_path": "transcript.md",
                        "latest_path": "latest.md",
                        "intake_path": "intake.md",
                        "discovery_path": "discovery.json",
                    }
                ),
                encoding="utf-8",
            )
            discovery.write_text(
                json.dumps(
                    {
                        "contract_version": "public_permalink_discovery.v1",
                        "entrypoints": {
                            "intake_md": "intake.md",
                            "transcript_md": "transcript.md",
                            "latest_md": "latest.md",
                            "status_json": "status.json",
                            "episodes_dir": "episodes/",
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = {
                "public_permalink_latest_path": str(latest),
                "public_permalink_intake_path": str(intake),
                "public_permalink_status_path": str(status),
                "public_permalink_discovery_path": str(discovery),
            }

            result = evaluate_intake_readiness(payload)
            self.assertTrue(result["ok"])
            self.assertEqual(result["errors"], [])

    def test_evaluate_intake_readiness_missing_files(self) -> None:
        result = evaluate_intake_readiness({})
        self.assertFalse(result["ok"])
        self.assertIn("missing:public_permalink_latest_path", result["errors"])
        self.assertIn("missing:public_permalink_intake_path", result["errors"])


if __name__ == "__main__":
    unittest.main()
