#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SHOW_KEY="jack_mallers_show"
MIN_CAPTION_WORDS="${MIN_CAPTION_WORDS:-120}"

cd "$REPO_ROOT"
source .venv311/bin/activate

python -m bitpod discover --show "$SHOW_KEY"
python -m bitpod sync \
  --show "$SHOW_KEY" \
  --max-episodes 1 \
  --source-policy balanced \
  --min-caption-words "$MIN_CAPTION_WORDS"

python - <<'PY'
import json
import sys
from pathlib import Path

status_path = Path("transcripts/jack_mallers_show/mallers_bitpod_status.json")
if not status_path.exists():
    print(f"ERROR: missing status artifact: {status_path}")
    raise SystemExit(2)

payload = json.loads(status_path.read_text(encoding="utf-8"))
run_status = payload.get("run_status")
included = bool(payload.get("included_in_pointer"))
if run_status == "ok" and included:
    print("Weekly run OK: latest episode included in pointer")
    raise SystemExit(0)

print("Weekly run FAILED or latest not included in pointer")
print(f"run_status={run_status} included_in_pointer={included}")
print(f"failure_stage={payload.get('failure_stage')} reason={payload.get('failure_reason')}")
raise SystemExit(1)
PY
