#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.track_reports import write_track_run_summary


def main() -> int:
    parser = argparse.ArgumentParser(prog="render_weekly_run_summary")
    parser.add_argument("--show", required=True)
    parser.add_argument(
        "--track",
        required=True,
        choices=["legacy_tuesday_track", "experimental_track", "mallers_weekly_fetch"],
    )
    parser.add_argument("--feed-mode", required=True)
    args = parser.parse_args()

    md_path, json_path, summary = write_track_run_summary(
        show_key=args.show,
        track_name=args.track,
        feed_mode=args.feed_mode,
    )
    print(
        json.dumps(
            {
                "summary_md": str(md_path),
                "summary_json": str(json_path),
                "success": bool(summary.get("success")),
                "gpt_consumed": bool(summary.get("gpt_consumed")),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
