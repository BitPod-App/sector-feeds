from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class WeeklyCriticalBundleTests(unittest.TestCase):
    def test_bundle_is_incomplete_when_two_or_more_metrics_blocked(self) -> None:
        report = """status_header: STRICT + INCOMPLETE

data_table:
metric | value | timestamp_utc | source_url | source_type | confidence_0_to_100 | confidence_override_reason | scoring_usable_yes_no
--- | --- | --- | --- | --- | --- | --- | ---
spot_btc | 64000 | 2026-02-27T00:00:00Z | https://example.com/spot | secondary | 92 | none | yes
etf_net_flows | MISSING | N/A | N/A | none | 0 | missing | no
derivatives_funding_oi_liquidations | MISSING | N/A | N/A | none | 0 | missing | no
move_index | 120 | 2026-02-27T00:00:00Z | https://example.com/move | secondary | 70 | fallback | yes
dfii10 | MISSING | N/A | N/A | none | 0 | missing | no
dgs10 | MISSING | N/A | N/A | none | 0 | missing | no
broad_usd | MISSING | N/A | N/A | none | 0 | missing | no
usdjpy | MISSING | N/A | N/A | none | 0 | missing | no
rrp | MISSING | N/A | N/A | none | 0 | missing | no
tga | MISSING | N/A | N/A | none | 0 | missing | no
"""
        script = Path(__file__).resolve().parents[1] / "scripts" / "generate_weekly_critical_bundle.py"

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_path = tmp_path / "report.md"
            output_path = tmp_path / "bundle.json"
            report_path.write_text(report, encoding="utf-8")

            subprocess.run(
                [
                    "python3",
                    str(script),
                    "--report-md",
                    str(report_path),
                    "--output-json",
                    str(output_path),
                    "--as-of-utc",
                    "2026-02-27T00:00:00Z",
                    "--run-id",
                    "test_run",
                ],
                check=True,
            )

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["gate_status"], "INCOMPLETE")
            self.assertGreaterEqual(payload["critical_metrics_missing_or_blocked_count"], 2)
            self.assertEqual(payload["critical_metrics_total"], 10)


if __name__ == "__main__":
    unittest.main()
