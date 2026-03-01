#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
MAX_AGE_DAYS="${2:-9}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" "$MAX_AGE_DAYS" <<'PY'
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

show_key = sys.argv[1]
max_age_days = int(sys.argv[2])
shows = json.loads(Path("shows.json").read_text(encoding="utf-8"))
show = ((shows or {}).get("shows") or {}).get(show_key) or {}
if not show:
    raise SystemExit(f"Unknown show_key: {show_key}")

stem = Path(show.get("stable_pointer") or "jack_mallers.md").stem
status_path = Path("transcripts") / show_key / f"{stem}_status.json"
if not status_path.exists():
    raise SystemExit(f"Missing status artifact: {status_path}")

status = json.loads(status_path.read_text(encoding="utf-8"))
raw = status.get("run_finished_at_utc") or status.get("run_started_at_utc")
if not raw:
    print("stale_check=FAIL missing_run_timestamp")
    raise SystemExit(1)
try:
    ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
except ValueError:
    print("stale_check=FAIL invalid_run_timestamp")
    raise SystemExit(1)

age = datetime.now(timezone.utc) - ts
ok = age <= timedelta(days=max_age_days)
print(f"show_key={show_key}")
print(f"max_age_days={max_age_days}")
print(f"run_finished_at_utc={ts.isoformat()}")
print(f"age_days={age.total_seconds()/86400:.2f}")
print(f"stale_check={'PASS' if ok else 'FAIL'}")
raise SystemExit(0 if ok else 1)
PY

