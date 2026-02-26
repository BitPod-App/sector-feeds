#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key>"
  exit 2
fi

SHOW_KEY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$REPO_ROOT/artifacts"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" <<'PY'
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

show_key = sys.argv[1]
repo_root = Path(".")
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_json = repo_root / "transcripts" / show_key / f"{stem}_status.json"
report_name = re.sub(r"[^a-z0-9]+", "_", show_key.lower()).strip("_") + "_weekly_report.md"
report_md = repo_root / "artifacts" / report_name

now = datetime.now(timezone.utc)

if not status_json.exists():
    report_md.write_text(
        f"# {show_key} Weekly Report\n\n"
        "## FAILED\n"
        f"- reason: missing `{status_json}`\n"
        f"- action: run `bash scripts/run_show_weekly.sh {show_key}`\n",
        encoding="utf-8",
    )
    raise SystemExit(1)

payload = json.loads(status_json.read_text(encoding="utf-8"))
finished_raw = payload.get("run_finished_at_utc")
finished_at = None
if isinstance(finished_raw, str) and finished_raw:
    try:
        finished_at = datetime.fromisoformat(finished_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        finished_at = None

is_recent = bool(finished_at and finished_at >= (now - timedelta(days=9)))
included = bool(payload.get("included_in_pointer"))
run_status = payload.get("run_status", "failed")

success = run_status == "ok" and included and is_recent
headline = "SUCCESS" if success else "FAILED"

lines = [
    f"# {show_key} Weekly Report",
    "",
    f"## {headline}",
    f"- generated_at_utc: `{now.isoformat()}`",
    f"- run_id: `{payload.get('run_id')}`",
    f"- run_status: `{run_status}`",
    f"- latest_episode_title: `{payload.get('latest_episode_title')}`",
    f"- latest_episode_guid: `{payload.get('latest_episode_guid')}`",
    f"- latest_episode_published_at_utc: `{payload.get('latest_episode_published_at_utc')}`",
    f"- included_in_pointer: `{included}`",
    f"- run_is_recent: `{is_recent}`",
    f"- pointer_path: `{payload.get('pointer_path')}`",
    f"- plain_artifact_path: `{payload.get('plain_artifact_path')}`",
    f"- segments_artifact_path: `{payload.get('segments_artifact_path')}`",
    f"- gpt_review_request_path: `{payload.get('gpt_review_request_path')}`",
]

if not success:
    lines.extend(
        [
            "",
            "## Failure Context",
            f"- failure_stage: `{payload.get('failure_stage')}`",
            f"- failure_reason: `{payload.get('failure_reason')}`",
            f"- suggested_next_action: `{payload.get('suggested_next_action')}`",
            f"- retry_command: `bash scripts/run_show_weekly.sh {show_key}`",
            "- gpt_action: upload review request + available artifacts to GPT for QA feedback",
        ]
    )

report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Report written to: {report_md}")
raise SystemExit(0 if success else 1)
PY
