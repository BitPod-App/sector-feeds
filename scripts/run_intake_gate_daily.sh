#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/run_intake_gate_daily.sh <intake_json_path> <deck_id> [log_jsonl_path]

Runs default intake handshake validation and writes:
  1) machine-readable daily status JSON
  2) human-readable daily summary Markdown
  3) retained daily history JSONL
  4) M-5 tracker Markdown
  5) drift report (JSON + Markdown)

Default outputs:
  - artifacts/coordination/intake_gate_daily_status.json
  - artifacts/coordination/intake_gate_daily_summary.md
  - artifacts/coordination/intake_gate_daily_log.jsonl
  - artifacts/coordination/m5_tracker.md
  - artifacts/coordination/intake_gate_daily_drift_report.json
  - artifacts/coordination/intake_gate_daily_drift_report.md

Policy-as-code:
  - milestones/m5_policy.json

Optional env vars:
  BITPOD_INTAKE_POLICY_JSON=<path>
  BITPOD_INTAKE_DAILY_STATUS_JSON=<path>
  BITPOD_INTAKE_DAILY_SUMMARY_MD=<path>
  BITPOD_INTAKE_DAILY_M5_TRACKER_MD=<path>
  BITPOD_INTAKE_DAILY_DRIFT_JSON=<path>
  BITPOD_INTAKE_DAILY_DRIFT_MD=<path>
  BITPOD_TAYLOR_KEEPALIVE_JSON=<path>
  BITPOD_TAYLOR_AUTOPOST=0|1   (default: 0)
  BITPOD_TAYLOR_AUTOPOST_OUT_MD=<path>
  BITPOD_INTAKE_DAILY_HANDSHAKE_JSON=<path>
  BITPOD_INTAKE_DAILY_V1_DIAG_JSON=<path>
  BITPOD_INTAKE_DAILY_ENABLE_V1_DIAGNOSTIC=0|1   (default: 1)
USAGE
}

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  usage
  exit 2
fi

INTAKE_JSON="$1"
DECK_ID="$2"
LOG_JSONL="${3:-artifacts/coordination/intake_gate_daily_log.jsonl}"
POLICY_JSON="${BITPOD_INTAKE_POLICY_JSON:-milestones/m5_policy.json}"
STATUS_JSON="${BITPOD_INTAKE_DAILY_STATUS_JSON:-artifacts/coordination/intake_gate_daily_status.json}"
SUMMARY_MD="${BITPOD_INTAKE_DAILY_SUMMARY_MD:-artifacts/coordination/intake_gate_daily_summary.md}"
M5_TRACKER_MD="${BITPOD_INTAKE_DAILY_M5_TRACKER_MD:-artifacts/coordination/m5_tracker.md}"
DRIFT_JSON="${BITPOD_INTAKE_DAILY_DRIFT_JSON:-artifacts/coordination/intake_gate_daily_drift_report.json}"
DRIFT_MD="${BITPOD_INTAKE_DAILY_DRIFT_MD:-artifacts/coordination/intake_gate_daily_drift_report.md}"
TAYLOR_KEEPALIVE_JSON="${BITPOD_TAYLOR_KEEPALIVE_JSON:-artifacts/coordination/taylor_runtime_keepalive.json}"
TAYLOR_AUTOPOST="${BITPOD_TAYLOR_AUTOPOST:-0}"
TAYLOR_AUTOPOST_OUT_MD="${BITPOD_TAYLOR_AUTOPOST_OUT_MD:-artifacts/coordination/intake_gate_daily_taylor_autopost.md}"
HANDSHAKE_OUT="${BITPOD_INTAKE_DAILY_HANDSHAKE_JSON:-artifacts/coordination/intake_gate_daily_v2_default.json}"
V1_DIAG_OUT="${BITPOD_INTAKE_DAILY_V1_DIAG_JSON:-artifacts/coordination/intake_gate_daily_v1_rollback_diagnostic.json}"
ENABLE_V1_DIAGNOSTIC="${BITPOD_INTAKE_DAILY_ENABLE_V1_DIAGNOSTIC:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f "$POLICY_JSON" ]; then
  echo "FATAL: policy file not found: $POLICY_JSON" >&2
  exit 1
fi

read -r POLICY_TARGET <<<"$(python3 - "$POLICY_JSON" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from bitpod.intake_gate_policy import load_policy

policy = load_policy(Path(sys.argv[1]))
print(str(policy["required_validation_target"]))
PY
)"

mkdir -p "$(dirname "$HANDSHAKE_OUT")"

set +e
BITPOD_INTAKE_VALIDATION_TARGET="$POLICY_TARGET" \
  bash "$SCRIPT_DIR/check_bitregime_core_intake_handshake.sh" "$INTAKE_JSON" "$DECK_ID" "$HANDSHAKE_OUT"
TARGET_EXIT_CODE="$?"
set -e

if [ "$ENABLE_V1_DIAGNOSTIC" = "1" ]; then
  BITPOD_INTAKE_VALIDATION_TARGET=bitregime_core_intake.v1 \
    bash "$SCRIPT_DIR/check_bitregime_core_intake_handshake.sh" "$INTAKE_JSON" "$DECK_ID" "$V1_DIAG_OUT" || true
fi

if ! python3 - "$POLICY_JSON" "$HANDSHAKE_OUT" "$V1_DIAG_OUT" "$LOG_JSONL" "$STATUS_JSON" "$SUMMARY_MD" "$M5_TRACKER_MD" "$DRIFT_JSON" "$DRIFT_MD" "$TAYLOR_KEEPALIVE_JSON" "$INTAKE_JSON" "$DECK_ID" "$ENABLE_V1_DIAGNOSTIC" "$TARGET_EXIT_CODE" <<'PY'
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bitpod.intake_gate_policy import close_ready, evaluate_drift, guardrail, load_policy, validate_status_contract

policy_path = Path(sys.argv[1])
handshake_v2_path = Path(sys.argv[2])
handshake_v1_path = Path(sys.argv[3])
log_path = Path(sys.argv[4])
status_path = Path(sys.argv[5])
summary_path = Path(sys.argv[6])
m5_tracker_path = Path(sys.argv[7])
drift_json_path = Path(sys.argv[8])
drift_md_path = Path(sys.argv[9])
taylor_keepalive_path = Path(sys.argv[10])
intake_json_path = Path(sys.argv[11]).expanduser().resolve()
deck_id = sys.argv[12]
enable_v1_diagnostic = (sys.argv[13].strip() == "1")
target_exit_code = int(sys.argv[14])

policy = load_policy(policy_path)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _classify_error(err: str) -> str:
    if err.startswith("missing_file:"):
        return "missing_file"
    if err.startswith("unsupported_contract_version:"):
        return "unsupported_contract_version"
    if err.startswith("invalid_json:"):
        return "invalid_json"
    if err.startswith("missing:"):
        return "missing_field"
    if err.startswith("invalid:"):
        return "field_validation_error"
    if err.startswith("duplicate:"):
        return "duplicate_field_value"
    if err.startswith("invalid_episode:"):
        return "invalid_episode_row"
    if err.startswith("unsupported_validation_target:"):
        return "unsupported_validation_target"
    return "unknown_validation_error"


def _row_is_green(row: dict) -> bool:
    if "gate_green" in row:
        return bool(row.get("gate_green"))
    return bool(row.get("all_green"))


v2_obj = _load_json(handshake_v2_path)
v1_obj = _load_json(handshake_v1_path) if enable_v1_diagnostic else {}
taylor_keepalive_obj = _load_json(taylor_keepalive_path)
contract_errors = sorted(list(v2_obj.get("contract_errors") or []))
failure_categories = [_classify_error(e) for e in contract_errors]
failure_counts = dict(Counter(failure_categories))

gate_green = bool(v2_obj.get("contract_ok")) and target_exit_code == 0
now = datetime.now(timezone.utc)

history_rows: list[dict] = []
if log_path.exists():
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            history_rows.append(obj)

record = {
    "status_schema_version": "intake_gate_daily_status.v2",
    "policy_version": str(policy["policy_version"]),
    "milestone": str(policy["milestone"]),
    "milestone_status": str(policy.get("milestone_status") or "IN_PROGRESS"),
    "owner_oncall": str(policy.get("owner_oncall") or "single_engineer_mode"),
    "date_utc": now.strftime("%Y-%m-%d"),
    "timestamp_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "branch": os.environ.get("GITHUB_REF_NAME", "local"),
    "intake_json_path": str(intake_json_path),
    "producer_artifact_present": intake_json_path.exists(),
    "deck_id": deck_id,
    "gate_mode": "policy_driven_default",
    "required_validation_target": str(policy["required_validation_target"]),
    "close_ready_required_consecutive_greens": int(policy["close_ready_consecutive_greens"]),
    "v2_default_output_path": str(handshake_v2_path.resolve()),
    "v2_contract_ok": gate_green,
    "contract_ok": gate_green,
    "contract_errors": contract_errors,
    "failure_reason_categories": sorted(set(failure_categories)),
    "failure_reason_counts": failure_counts,
    "gate_green": gate_green,
    "all_green": gate_green,
    "rollback_diagnostic_v1_enabled": enable_v1_diagnostic,
    "rollback_diagnostic_v1_output_path": str(handshake_v1_path.resolve()) if enable_v1_diagnostic else None,
    "rollback_diagnostic_v1_contract_ok": bool(v1_obj.get("contract_ok")) if enable_v1_diagnostic else None,
    "rollback_guardrail_threshold": int(policy["rollback_guardrail_consecutive_failures"]),
    "taylor_keepalive_json_path": str(taylor_keepalive_path.resolve()),
    "taylor_runtime_keepalive_ok": bool(taylor_keepalive_obj.get("keepalive_ok")) if taylor_keepalive_obj else False,
    "taylor_runtime_keepalive_reason": str(taylor_keepalive_obj.get("reason") or "missing_keepalive_artifact")
    if taylor_keepalive_obj
    else "missing_keepalive_artifact",
}

rows_with_current = [*history_rows, record]
consecutive_failures = 0
for row in reversed(rows_with_current):
    if _row_is_green(row):
        break
    consecutive_failures += 1

consecutive_greens = 0
for row in reversed(rows_with_current):
    if _row_is_green(row):
        consecutive_greens += 1
    else:
        break

record["consecutive_failures"] = consecutive_failures
record["consecutive_greens"] = consecutive_greens
record["m5_close_ready_3_consecutive_greens"] = close_ready(consecutive_greens, policy)
if record["milestone_status"] == "DONE":
    # Administrative closure wins over rolling local log-window counters.
    record["m5_close_ready_3_consecutive_greens"] = True
guardrail_triggered, escalation = guardrail(consecutive_failures, policy)
record["rollback_guardrail_triggered"] = guardrail_triggered
record["freeze_action_on_guardrail"] = str(policy["freeze_action_on_guardrail"])
record["escalation"] = escalation

status_contract_errors = validate_status_contract(record)
record["status_contract_ok"] = (len(status_contract_errors) == 0)
record["status_contract_errors"] = status_contract_errors
if not record["status_contract_ok"]:
    record["gate_green"] = False
    record["all_green"] = False

drift = evaluate_drift(policy, record)
record["drift_ok"] = bool(drift["drift_ok"])
record["drift_failed_checks"] = [c["name"] for c in drift["checks"] if not bool(c["ok"])]
if not record["drift_ok"]:
    record["gate_green"] = False
    record["all_green"] = False

log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record, sort_keys=True) + "\n")

status_path.parent.mkdir(parents=True, exist_ok=True)
status_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

drift_payload = {
    "timestamp_utc": record["timestamp_utc"],
    "policy_json_path": str(policy_path.resolve()),
    "status_json_path": str(status_path.resolve()),
    "drift_ok": bool(drift["drift_ok"]),
    "checks": drift["checks"],
}
drift_json_path.parent.mkdir(parents=True, exist_ok=True)
drift_json_path.write_text(json.dumps(drift_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

drift_md_lines = [
    "# Intake Gate Daily Drift Report",
    "",
    f"- timestamp_utc: `{record['timestamp_utc']}`",
    f"- policy_json: `{policy_path.resolve()}`",
    f"- status_json: `{status_path.resolve()}`",
    f"- drift_ok: `{drift_payload['drift_ok']}`",
    "",
    "## Checks",
]
for check in drift["checks"]:
    drift_md_lines.append(
        "- "
        + f"{check['name']}: expected=`{check['expected']}` observed=`{check['observed']}` ok=`{check['ok']}`"
    )
drift_md_path.parent.mkdir(parents=True, exist_ok=True)
drift_md_path.write_text("\n".join(drift_md_lines) + "\n", encoding="utf-8")

summary_lines = [
    "# Intake Gate Daily Summary",
    "",
    f"- timestamp_utc: `{record['timestamp_utc']}`",
    f"- branch: `{record['branch']}`",
    f"- owner_context: `{record['owner_oncall']}`",
    f"- intake_json_path: `{record['intake_json_path']}`",
    f"- deck_id: `{record['deck_id']}`",
    f"- required_validation_target: `{record['required_validation_target']}`",
    f"- contract_ok: `{record['contract_ok']}`",
    f"- status_contract_ok: `{record['status_contract_ok']}`",
    f"- drift_ok: `{record['drift_ok']}`",
    f"- taylor_runtime_keepalive_ok: `{record['taylor_runtime_keepalive_ok']}`",
    f"- taylor_runtime_keepalive_reason: `{record['taylor_runtime_keepalive_reason']}`",
    f"- gate_green: `{record['gate_green']}`",
    f"- producer_artifact_present: `{record['producer_artifact_present']}`",
    f"- consecutive_failures: `{record['consecutive_failures']}`",
    f"- rollback_guardrail_threshold: `{record['rollback_guardrail_threshold']}`",
    f"- rollback_guardrail_triggered: `{record['rollback_guardrail_triggered']}`",
    f"- escalation: `{record['escalation']}`",
    f"- m5_close_ready_3_consecutive_greens: `{record['m5_close_ready_3_consecutive_greens']}`",
    f"- status_json: `{status_path.resolve()}`",
    f"- history_log_jsonl: `{log_path.resolve()}`",
    f"- handshake_target_json: `{handshake_v2_path.resolve()}`",
    f"- drift_json: `{drift_json_path.resolve()}`",
    f"- drift_md: `{drift_md_path.resolve()}`",
    f"- taylor_keepalive_json: `{taylor_keepalive_path.resolve()}`",
]
if enable_v1_diagnostic:
    summary_lines.append(f"- rollback_diagnostic_v1_contract_ok: `{record['rollback_diagnostic_v1_contract_ok']}`")
    summary_lines.append(f"- rollback_diagnostic_v1_json: `{handshake_v1_path.resolve()}`")

summary_lines.extend(["", "## Failure Classification"])
if contract_errors:
    for cat, count in sorted(failure_counts.items()):
        summary_lines.append(f"- {cat}: `{count}`")
    summary_lines.extend(["", "## Contract Errors"])
    for err in contract_errors:
        summary_lines.append(f"- `{err}`")
else:
    summary_lines.append("- none")

if status_contract_errors:
    summary_lines.extend(["", "## Status Contract Errors", *[f"- `{e}`" for e in status_contract_errors]])
if not drift_payload["drift_ok"]:
    summary_lines.extend(["", "## Drift Check Failures", *[f"- `{name}`" for name in record["drift_failed_checks"]]])

summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

m5_lines = [
    "# M-5 Tracker",
    "",
    f"- timestamp_utc: `{record['timestamp_utc']}`",
    f"- normalized_entry: `milestone={record['milestone']} | status={record['milestone_status']} | blocked=false`",
    f"- owner_context: `{record['owner_oncall']}`",
    f"- contract_ok: `{record['contract_ok']}`",
    f"- required_validation_target: `{record['required_validation_target']}`",
    f"- consecutive_greens: `{record['consecutive_greens']}` / `{record['close_ready_required_consecutive_greens']}`",
    f"- m5_close_ready_3_consecutive_greens: `{record['m5_close_ready_3_consecutive_greens']}`",
    f"- consecutive_failures: `{record['consecutive_failures']}`",
    f"- rollback_guardrail_threshold: `{record['rollback_guardrail_threshold']}`",
    f"- rollback_guardrail_triggered: `{record['rollback_guardrail_triggered']}`",
    f"- escalation: `{record['escalation']}`",
    f"- drift_ok: `{record['drift_ok']}`",
    f"- taylor_runtime_keepalive_ok: `{record['taylor_runtime_keepalive_ok']}`",
    f"- taylor_runtime_keepalive_reason: `{record['taylor_runtime_keepalive_reason']}`",
    f"- daily_status_json: `{status_path.resolve()}`",
    f"- daily_drift_report_md: `{drift_md_path.resolve()}`",
]
if contract_errors:
    m5_lines.extend(["", "## Failure Categories"])
    for cat, count in sorted(failure_counts.items()):
        m5_lines.append(f"- {cat}: `{count}`")
else:
    m5_lines.extend(["", "## Failure Categories", "- none"])

m5_tracker_path.parent.mkdir(parents=True, exist_ok=True)
m5_tracker_path.write_text("\n".join(m5_lines) + "\n", encoding="utf-8")

print(json.dumps(record, indent=2, sort_keys=True))
raise SystemExit(0 if record["gate_green"] else 1)
PY
then
  echo "FATAL: intake gate daily check RED (see $STATUS_JSON, $SUMMARY_MD, $DRIFT_MD, and $LOG_JSONL)" >&2
  exit 1
fi

if [ "$TAYLOR_AUTOPOST" = "1" ]; then
  bash "$SCRIPT_DIR/taylor_autopost_intake_context.sh" \
    "$STATUS_JSON" \
    "$SUMMARY_MD" \
    "$DRIFT_MD" \
    "$M5_TRACKER_MD" \
    "$TAYLOR_AUTOPOST_OUT_MD" || true
fi

echo "intake_gate_daily=GREEN"
