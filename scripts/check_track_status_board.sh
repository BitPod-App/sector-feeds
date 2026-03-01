#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

bash "$SCRIPT_DIR/render_track_status_board.sh" "$SHOW_KEY" >/dev/null

python3 - "$SHOW_KEY" <<'PY'
import json
import sys
from pathlib import Path

show_key = sys.argv[1]
path = Path("artifacts") / f"{show_key}_track_status_board.json"
obj = json.loads(path.read_text(encoding="utf-8"))

ok = True
checks = []

def mark(name: str, value: bool) -> None:
    global ok
    checks.append((name, value))
    if not value:
        ok = False

mark("run_status_ok", obj.get("run_status") == "ok")
mark("ready_via_permalink", bool(obj.get("ready_via_permalink")))
mark("intake_ready", bool(obj.get("intake_ready")))
mark("legacy_tuesday_success", (obj.get("legacy_tuesday") or {}).get("report_state") == "success")
mark("legacy_friday_success", (obj.get("legacy_friday") or {}).get("report_state") == "success")
mark("experimental_shared_contract_ready", bool((obj.get("experimental") or {}).get("shared_permalink_contract_ready")))

sp = obj.get("shared_permalink_contract") or {}
mark("transcript_url_present", bool(sp.get("transcript_url")))
mark("status_url_present", bool(sp.get("status_url")))
mark("discovery_url_present", bool(sp.get("discovery_url")))

print(f"show_key={show_key}")
for name, value in checks:
    print(f"{name}={'PASS' if value else 'FAIL'}")

if ok:
    print("track_status=PASS")
    raise SystemExit(0)
print("track_status=FAIL")
raise SystemExit(1)
PY

