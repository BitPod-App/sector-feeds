#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

show_key = sys.argv[1]
repo = Path(".")
art = repo / "artifacts"
coord = art / "coordination"
coord.mkdir(parents=True, exist_ok=True)

board_json = art / f"{show_key}_track_status_board.json"
if not board_json.exists():
    raise SystemExit(f"Missing board JSON: {board_json}. Run `make track-status-board SHOW_KEY={show_key}` first.")

board = json.loads(board_json.read_text(encoding="utf-8"))
private_deploy_file = art / "private" / "coordination" / "latest_deploy_url.txt"
legacy_deploy_file = coord / "latest_deploy_url.txt"
deploy_file = private_deploy_file if private_deploy_file.exists() else legacy_deploy_file
deploy_url = deploy_file.read_text(encoding="utf-8").strip() if deploy_file.exists() else None

status = board.get("shared_permalink_contract") or {}
lines = [
    f"# Current Handoff: {show_key}",
    "",
    f"- generated_at_utc: `{datetime.now(timezone.utc).isoformat()}`",
    f"- track_status: `{'PASS' if board.get('intake_ready') and board.get('ready_via_permalink') else 'CHECK'}`",
    f"- run_status: `{board.get('run_status')}`",
    f"- intake_ready: `{board.get('intake_ready')}`",
    f"- ready_via_permalink: `{board.get('ready_via_permalink')}`",
    "",
    "## Track States",
    f"- legacy_tuesday: `{(board.get('legacy_tuesday') or {}).get('report_state')}`",
    f"- legacy_friday: `{(board.get('legacy_friday') or {}).get('report_state')}`",
    f"- experimental_shared_contract_ready: `{(board.get('experimental') or {}).get('shared_permalink_contract_ready')}`",
    "",
    "## Shared Contract URLs",
    f"- transcript_url: `{status.get('transcript_url')}`",
    f"- status_url: `{status.get('status_url')}`",
    f"- discovery_url: `{status.get('discovery_url')}`",
]
if deploy_url:
    lines.extend(["", "## Latest Deploy", f"- preview_url: `{deploy_url}`"])

out = coord / "current_handoff.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out)
PY
