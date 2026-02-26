#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.cost_meter import estimate_tokens_from_text, excerpt_text

BRIDGE_ROOT = Path("/Users/cjarguello/bitpod-app/tools/gpt_bridge")


def _extract_gpt_payload(stdout: str) -> str:
    marker = "GPT:"
    idx = stdout.rfind(marker)
    if idx < 0:
        return ""
    return stdout[idx + len(marker) :].strip()


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt_report_from_transcript")
    parser.add_argument("--transcript-path", required=True)
    parser.add_argument("--report-name", required=True, help="e.g. gpt-bitreport-pods-all-20260225-1856.md")
    parser.add_argument("--show-key", default="jack_mallers_show")
    parser.add_argument("--full-text", action="store_true", help="Send full transcript text to GPT (costlier).")
    parser.add_argument("--max-chars", type=int, default=6000, help="Max chars when not using --full-text.")
    args = parser.parse_args()

    transcript_path = Path(args.transcript_path).expanduser().resolve()
    if not transcript_path.exists():
        raise SystemExit(f"ERROR: transcript not found: {transcript_path}")

    raw = transcript_path.read_text(encoding="utf-8", errors="ignore")
    payload_mode = "full" if args.full_text else "excerpt"
    transcript_payload = raw if args.full_text else excerpt_text(raw, max_chars=max(1000, args.max_chars))

    prompt = (
        f"@gpt Generate ONLY markdown for a file named {args.report_name}. "
        f"Requirements: include a top heading, include a line exactly 'included_shows: {args.show_key}', "
        "include status assessment usable/degraded/failed, 3-6 key macro/bitcoin takeaways, and 2 quality notes "
        "about transcript reliability. Keep concise.\n\n"
        "--- TRANSCRIPT START ---\n"
        f"{transcript_payload}\n"
        "--- TRANSCRIPT END ---\n"
    )

    proc = subprocess.run(
        ["./bridge_chat.sh", "chat", "--stdin"],
        cwd=str(BRIDGE_ROOT),
        input=prompt,
        capture_output=True,
        text=True,
    )
    stdout = proc.stdout
    stderr = proc.stderr
    gpt_md = _extract_gpt_payload(stdout)

    report_dir = REPO_ROOT / "artifacts" / "gpt-bitreports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / args.report_name
    if gpt_md:
        report_path.write_text(gpt_md.rstrip() + "\n", encoding="utf-8")

    meter_dir = REPO_ROOT / "artifacts" / "cost-meter"
    meter_dir.mkdir(parents=True, exist_ok=True)
    meter_path = meter_dir / "bridge_cost_estimates.jsonl"
    entry = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "show_key": args.show_key,
        "transcript_path": str(transcript_path),
        "report_path": str(report_path),
        "mode": payload_mode,
        "input_chars": len(prompt),
        "input_tokens_est": estimate_tokens_from_text(prompt),
        "output_chars": len(gpt_md),
        "output_tokens_est": estimate_tokens_from_text(gpt_md),
        "bridge_returncode": proc.returncode,
    }
    with meter_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    print(json.dumps({"report_path": str(report_path), "meter_path": str(meter_path), "entry": entry}, indent=2))
    if stderr.strip():
        print(stderr.strip())
    return 0 if proc.returncode == 0 and bool(gpt_md) else 1


if __name__ == "__main__":
    raise SystemExit(main())
