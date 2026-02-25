#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <show_key> <feedback_markdown_path>"
  exit 2
fi

SHOW_KEY="$1"
FEEDBACK_PATH_INPUT="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

.venv311/bin/python - "$SHOW_KEY" "$FEEDBACK_PATH_INPUT" "$REPO_ROOT" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

show_key = sys.argv[1]
feedback_input = Path(sys.argv[2]).expanduser().resolve()
repo_root = Path(sys.argv[3]).resolve()

if not feedback_input.exists():
    print(f"ERROR: feedback file not found: {feedback_input}")
    raise SystemExit(2)

shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_json = repo_root / "transcripts" / show_key / f"{stem}_status.json"
if not status_json.exists():
    print(f"ERROR: missing status file: {status_json}")
    raise SystemExit(2)

status = json.loads(status_json.read_text(encoding="utf-8"))
slug = re.sub(r"[^a-z0-9]+", "_", show_key.lower()).strip("_")
ack_path = repo_root / "artifacts" / f"{slug}_gpt_ack.json"
ack_path.parent.mkdir(parents=True, exist_ok=True)

ack = {
    "show_key": show_key,
    "run_id": status.get("run_id"),
    "pointer_path": status.get("pointer_path"),
    "consumed": True,
    "feedback_path": str(feedback_input),
    "feedback_recorded_at_utc": datetime.now(timezone.utc).isoformat(),
}
ack_path.write_text(json.dumps(ack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"GPT feedback ack written: {ack_path}")
PY
