from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from bitpod.cli import main
from bitpod.retro_flags import load_flag_entries, summarize_flag_entries


class RetroFlagsTests(unittest.TestCase):
    def test_load_flag_entries_missing_file_returns_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.jsonl"
            self.assertEqual(load_flag_entries(path=path), [])

    def test_load_and_summarize_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "a",
                                "created_at_utc": "2026-03-01T00:00:00Z",
                                "status": "open",
                                "scope": "m9",
                            }
                        ),
                        json.dumps(
                            {
                                "id": "b",
                                "created_at_utc": "2026-03-01T00:01:00Z",
                                "status": "closed",
                                "scope": "ops",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            entries = load_flag_entries(path=path)
            summary = summarize_flag_entries(entries, limit=1)
            self.assertEqual(summary["total"], 2)
            self.assertEqual(summary["open"], 1)
            self.assertEqual(summary["closed"], 1)
            self.assertEqual(len(summary["recent"]), 1)
            self.assertEqual(summary["recent"][0]["id"], "b")

    def test_load_flag_entries_rejects_malformed_jsonl(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"id":"ok"}\n{"id":"bad"\n', encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_flag_entries(path=path)
            self.assertIn("line 2", str(ctx.exception))

    def test_cli_retro_flags_json(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "x",
                        "created_at_utc": "2026-03-01T00:00:00Z",
                        "status": "open",
                        "scope": "agent-process",
                        "source": "CJ",
                        "run_id": "M9-PROVING-RUN-003",
                        "note": "example",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            out = io.StringIO()
            with redirect_stdout(out):
                rc = main(["retro-flags", "--json", "--path", str(path)])
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["total"], 1)
            self.assertEqual(payload["open"], 1)
            self.assertEqual(payload["recent"][0]["id"], "x")

    def test_cli_retro_flags_bad_json_returns_2(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text("{bad}\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = main(["retro-flags", "--path", str(path)])
            self.assertEqual(rc, 2)
            self.assertIn("ERROR: Invalid JSONL", out.getvalue())


if __name__ == "__main__":
    unittest.main()
