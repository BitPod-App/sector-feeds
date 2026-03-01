#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bitpod.intake import evaluate_intake_readiness

show_key = sys.argv[1]
repo = Path(".")
artifacts = repo / "artifacts"
artifacts.mkdir(parents=True, exist_ok=True)

shows = json.loads((repo / "shows.json").read_text(encoding="utf-8"))
show = ((shows or {}).get("shows") or {}).get(show_key) or {}
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_path = repo / "transcripts" / show_key / f"{stem}_status.json"
status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
intake = evaluate_intake_readiness(status) if status else {"ok": False, "errors": ["missing_status_json"]}

def report_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"^##\s+SUCCESS\b", text, flags=re.MULTILINE):
        return "success"
    if re.search(r"^##\s+FAILED\b", text, flags=re.MULTILINE):
        return "failed"
    return "unknown"

tuesday_report = artifacts / f"{show_key}_tuesday_report.md"
friday_report = artifacts / f"{show_key}_friday_report.md"
experimental_snapshot = repo / "artifacts" / "private" / "experimental_weekly" / f"{show_key}_intake_snapshot.json"

exp_contract_ok = False
if experimental_snapshot.exists():
    try:
        exp = json.loads(experimental_snapshot.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        exp = {}
    c = exp.get("shared_permalink_contract") or {}
    exp_contract_ok = bool(c.get("public_permalink_transcript_url") and c.get("public_permalink_status_url") and c.get("public_permalink_discovery_url"))

lines = [
    f"# Track Status Board: {show_key}",
    "",
    f"- generated_at_utc: `{datetime.now(timezone.utc).isoformat()}`",
    f"- run_status: `{status.get('run_status')}`",
    f"- ready_via_permalink: `{bool(status.get('ready_via_permalink'))}`",
    f"- intake_ready: `{bool(intake.get('ok'))}`",
    "",
    "## Legacy Tuesday",
    f"- report_path: `{tuesday_report}`",
    f"- report_state: `{report_state(tuesday_report)}`",
    "",
    "## Legacy Friday",
    f"- report_path: `{friday_report}`",
    f"- report_state: `{report_state(friday_report)}`",
    "",
    "## Experimental",
    f"- intake_snapshot_path: `{experimental_snapshot}`",
    f"- shared_permalink_contract_ready: `{exp_contract_ok}`",
    "",
    "## Shared Permalink Contract",
    f"- transcript_url: `{status.get('public_permalink_transcript_url')}`",
    f"- status_url: `{status.get('public_permalink_status_url')}`",
    f"- discovery_url: `{status.get('public_permalink_discovery_url')}`",
]

if not intake.get("ok"):
    lines.extend(["", "## Intake Errors", *[f"- `{e}`" for e in intake.get("errors", [])]])

out = artifacts / f"{show_key}_track_status_board.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out)

payload = {
    "contract_version": "track_status_board.v1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "show_key": show_key,
    "run_status": status.get("run_status"),
    "ready_via_permalink": bool(status.get("ready_via_permalink")),
    "intake_ready": bool(intake.get("ok")),
    "legacy_tuesday": {
        "report_path": str(tuesday_report),
        "report_state": report_state(tuesday_report),
    },
    "legacy_friday": {
        "report_path": str(friday_report),
        "report_state": report_state(friday_report),
    },
    "experimental": {
        "intake_snapshot_path": str(experimental_snapshot),
        "shared_permalink_contract_ready": exp_contract_ok,
    },
    "shared_permalink_contract": {
        "transcript_url": status.get("public_permalink_transcript_url"),
        "status_url": status.get("public_permalink_status_url"),
        "discovery_url": status.get("public_permalink_discovery_url"),
    },
    "intake_errors": list(intake.get("errors") or []),
}
json_out = artifacts / f"{show_key}_track_status_board.json"
json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json_out)
PY
