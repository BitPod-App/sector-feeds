#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATUS_JSON="$REPO_ROOT/transcripts/jack_mallers_show/mallers_bitpod_status.json"
REPORT_MD="$REPO_ROOT/artifacts/mallers_weekly_report.md"

mkdir -p "$REPO_ROOT/artifacts"
cd "$REPO_ROOT"

python3 - <<'PY'
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

status_json = Path("transcripts/jack_mallers_show/mallers_bitpod_status.json")
report_md = Path("artifacts/mallers_weekly_report.md")

now = datetime.now(timezone.utc)

if not status_json.exists():
    report_md.write_text(
        "# Mallers Weekly Report\n\n"
        "## FAILED\n"
        "- reason: missing `mallers_bitpod_status.json`\n"
        "- action: run `scripts/run_mallers_weekly.sh`\n",
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
    "# Mallers Weekly Report",
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
]

if not success:
    lines.extend(
        [
            "",
            "## Failure Context",
            f"- failure_stage: `{payload.get('failure_stage')}`",
            f"- failure_reason: `{payload.get('failure_reason')}`",
            f"- suggested_next_action: `{payload.get('suggested_next_action')}`",
            "- retry_command: `bash scripts/run_mallers_weekly.sh`",
        ]
    )

report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
raise SystemExit(0 if success else 1)
PY

echo "Report written to: $REPORT_MD"
