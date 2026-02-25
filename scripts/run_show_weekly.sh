#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key> [min_caption_words]"
  exit 2
fi

SHOW_KEY="$1"
MIN_CAPTION_WORDS="${2:-${MIN_CAPTION_WORDS:-120}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
.venv311/bin/python -m bitpod discover --show "$SHOW_KEY"
.venv311/bin/python -m bitpod sync \
  --show "$SHOW_KEY" \
  --max-episodes 1 \
  --source-policy balanced \
  --min-caption-words "$MIN_CAPTION_WORDS"

.venv311/bin/python - "$SHOW_KEY" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

show_key = sys.argv[1]
repo_root = Path(sys.argv[2])
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
status_name = Path(stable_pointer).stem + "_status.json"
status_path = repo_root / "transcripts" / show_key / status_name
if not status_path.exists():
    print(f"ERROR: missing status artifact: {status_path}")
    raise SystemExit(2)

payload = json.loads(status_path.read_text(encoding="utf-8"))
run_status = payload.get("run_status")
included = bool(payload.get("included_in_pointer"))
if run_status == "ok" and included:
    print(f"Weekly run OK for {show_key}: latest episode included in pointer")
    raise SystemExit(0)

print(f"Weekly run FAILED for {show_key} or latest not included in pointer")
print(f"run_status={run_status} included_in_pointer={included}")
print(f"failure_stage={payload.get('failure_stage')} reason={payload.get('failure_reason')}")
raise SystemExit(1)
PY
