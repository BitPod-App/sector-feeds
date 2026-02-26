#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key>"
  exit 2
fi

SHOW_KEY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Generate/refresh weekly-style status report (may exit non-zero if failed); keep going for verification output.
if ! "$SCRIPT_DIR/report_show_weekly_status.sh" "$SHOW_KEY" >/tmp/bitpod_verify_report.log 2>&1; then
  true
fi

.venv311/bin/python - "$SHOW_KEY" "$REPO_ROOT" <<'PY'
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

show_key = sys.argv[1]
repo_root = Path(sys.argv[2])
now = datetime.now(timezone.utc)

shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_json = repo_root / "transcripts" / show_key / f"{stem}_status.json"
slug = re.sub(r"[^a-z0-9]+", "_", show_key.lower()).strip("_")
ack_json = repo_root / "artifacts" / f"{slug}_gpt_ack.json"
verify_md = repo_root / "artifacts" / f"{slug}_adhoc_verify.md"

if not status_json.exists():
    verify_md.write_text(
        f"# {show_key} Ad Hoc Verify\n\n"
        "## FAILED\n"
        f"- reason: missing status artifact `{status_json}`\n",
        encoding="utf-8",
    )
    raise SystemExit(1)

status = json.loads(status_json.read_text(encoding="utf-8"))
run_id = status.get("run_id")
run_status = status.get("run_status")
included = bool(status.get("included_in_pointer"))
finished_raw = status.get("run_finished_at_utc")
finished_at = None
if isinstance(finished_raw, str) and finished_raw:
    try:
        finished_at = datetime.fromisoformat(finished_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        finished_at = None
is_recent = bool(finished_at and finished_at >= (now - timedelta(days=9)))

ack = None
ack_matches = False
feedback_path = None
feedback_excerpt = None
if ack_json.exists():
    ack = json.loads(ack_json.read_text(encoding="utf-8"))
    ack_matches = ack.get("run_id") == run_id and bool(ack.get("consumed"))
    feedback_path = ack.get("feedback_path")
    if isinstance(feedback_path, str) and feedback_path:
        fp = Path(feedback_path)
        if fp.exists():
            text = fp.read_text(encoding="utf-8", errors="ignore")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            feedback_excerpt = " ".join(lines[:3])[:500]

gpt_consumed = bool(ack_matches)
overall_success = run_status == "ok" and included and is_recent and gpt_consumed
headline = "SUCCESS" if overall_success else "ATTENTION"

lines = [
    f"# {show_key} Ad Hoc Verify",
    "",
    f"## {headline}",
    f"- generated_at_utc: `{now.isoformat()}`",
    f"- run_id: `{run_id}`",
    f"- run_status: `{run_status}`",
    f"- included_in_pointer: `{included}`",
    f"- run_is_recent: `{is_recent}`",
    f"- gpt_consumed: `{gpt_consumed}`",
    f"- pointer_path: `{status.get('pointer_path')}`",
    f"- gpt_review_request_path: `{status.get('gpt_review_request_path')}`",
    f"- status_md_path: `{status.get('status_md_path')}`",
    f"- feedback_path: `{feedback_path}`",
]

if feedback_excerpt:
    lines.extend(["", "## Feedback Excerpt", feedback_excerpt])

if not overall_success:
    lines.extend(
        [
            "",
            "## Actions",
            f"- failure_stage: `{status.get('failure_stage')}`",
            f"- failure_reason: `{status.get('failure_reason')}`",
            f"- suggested_next_action: `{status.get('suggested_next_action')}`",
            f"- run_retry: `bash scripts/run_show_adhoc.sh {show_key}`",
            f"- gpt_ack_command: `bash scripts/record_show_gpt_feedback.sh {show_key} <feedback.md>`",
        ]
    )

verify_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Ad hoc verify report written: {verify_md}")
raise SystemExit(0 if overall_success else 1)
PY
