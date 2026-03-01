#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/run_intake_gate_triage.sh <intake_json_path> <deck_id> [log_jsonl_path]

One-command operator helper for intake gate triage:
  1) runs daily v2-default gate
  2) captures/prints summary and status artifacts
  3) on RED, runs rollback diagnostic path (v1 handshake)

Outputs:
  - artifacts/coordination/intake_gate_daily_status.json
  - artifacts/coordination/intake_gate_daily_summary.md
  - artifacts/coordination/intake_gate_triage.md
USAGE
}

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  usage
  exit 2
fi

INTAKE_JSON="$1"
DECK_ID="$2"
LOG_JSONL="${3:-artifacts/coordination/intake_gate_daily_log.jsonl}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

STATUS_JSON="${BITPOD_INTAKE_DAILY_STATUS_JSON:-artifacts/coordination/intake_gate_daily_status.json}"
SUMMARY_MD="${BITPOD_INTAKE_DAILY_SUMMARY_MD:-artifacts/coordination/intake_gate_daily_summary.md}"
TRIAGE_MD="artifacts/coordination/intake_gate_triage.md"
V1_DIAG_OUT="${BITPOD_INTAKE_DAILY_V1_DIAG_JSON:-artifacts/coordination/intake_gate_daily_v1_rollback_diagnostic.json}"

set +e
bash "$SCRIPT_DIR/run_intake_gate_daily.sh" "$INTAKE_JSON" "$DECK_ID" "$LOG_JSONL"
DAILY_EXIT="$?"
set -e

if [ "$DAILY_EXIT" -ne 0 ]; then
  BITPOD_INTAKE_VALIDATION_TARGET=bitregime_core_intake.v1 \
    bash "$SCRIPT_DIR/check_bitregime_core_intake_handshake.sh" "$INTAKE_JSON" "$DECK_ID" "$V1_DIAG_OUT" || true
fi

python3 - "$STATUS_JSON" "$SUMMARY_MD" "$TRIAGE_MD" "$INTAKE_JSON" "$DECK_ID" "$LOG_JSONL" "$V1_DIAG_OUT" "$DAILY_EXIT" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

status_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
triage_path = Path(sys.argv[3])
intake_json = sys.argv[4]
deck_id = sys.argv[5]
log_jsonl = sys.argv[6]
v1_diag = sys.argv[7]
daily_exit = int(sys.argv[8])

status = {}
if status_path.exists():
    try:
        obj = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            status = obj
    except json.JSONDecodeError:
        status = {}

contract_ok = bool(status.get("contract_ok"))
triggered = bool(status.get("rollback_guardrail_triggered"))
escalation = str(status.get("escalation") or "none")

lines = [
    "# Intake Gate Triage",
    "",
    "## Reproduce",
    f"- `bash scripts/run_intake_gate_daily.sh \"{intake_json}\" \"{deck_id}\" \"{log_jsonl}\"`",
    "",
    "## Verify",
    f"- `cat {status_path.resolve()}`",
    f"- `cat {summary_path.resolve()}`",
    f"- expected healthy marker: `contract_ok: true`",
    "",
    "## Rollback Path (Last Known-Good Behavior)",
    f"- `BITPOD_INTAKE_VALIDATION_TARGET=bitregime_core_intake.v1 bash scripts/check_bitregime_core_intake_handshake.sh \"{intake_json}\" \"{deck_id}\" \"{v1_diag}\"`",
    "- If rollback diagnostic is green, freeze new intake contract changes and route to incident triage before further rollout work.",
    "",
    "## Current Outcome",
    f"- contract_ok: `{contract_ok}`",
    f"- daily_exit_code: `{daily_exit}`",
    f"- rollback_guardrail_triggered: `{triggered}`",
    f"- escalation: `{escalation}`",
]

triage_path.parent.mkdir(parents=True, exist_ok=True)
triage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"triage_md": str(triage_path.resolve()), "contract_ok": contract_ok}, indent=2))
PY

if [ "$DAILY_EXIT" -ne 0 ]; then
  echo "intake_gate_triage=RED" >&2
  exit 1
fi
echo "intake_gate_triage=GREEN"
