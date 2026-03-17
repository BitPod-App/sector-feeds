#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/taylor_autopost_intake_context.sh <status_json> <summary_md> <drift_md> <tracker_md> [output_md]

Builds a compact QA+Context prompt from intake gate artifacts and posts it to Taylor via:
  taylor ask "<prompt>" --context <context_file>

Writes output markdown (default):
  artifacts/coordination/intake_gate_daily_taylor_autopost.md

Non-blocking by default (until post-M-9 hardening):
  - missing Taylor binary or ask failure exits 0 with skip note
  - set BITPOD_TAYLOR_AUTOPOST_STRICT=1 to make failures non-zero
USAGE
}

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
  usage
  exit 2
fi

STATUS_JSON="$1"
SUMMARY_MD="$2"
DRIFT_MD="$3"
TRACKER_MD="$4"
OUT_MD="${5:-artifacts/coordination/intake_gate_daily_taylor_autopost.md}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
cd "$REPO_ROOT"

TAYLOR_BIN="${TAYLOR_BIN:-}"
STRICT="${BITPOD_TAYLOR_AUTOPOST_STRICT:-0}"
if [ -z "$TAYLOR_BIN" ]; then
  if command -v taylor >/dev/null 2>&1; then
    TAYLOR_BIN="$(command -v taylor)"
  else
    TOOLS_ROOT="${TOOLS_ROOT:-$WORKSPACE_ROOT/bitpod-tools}"
    if [ -x "${TOOLS_ROOT}/taylor/bin/taylor" ]; then
      TAYLOR_BIN="${TOOLS_ROOT}/taylor/bin/taylor"
    fi
  fi
fi

mkdir -p "$(dirname "$OUT_MD")"

if [ -z "${TAYLOR_BIN}" ] || [ ! -x "${TAYLOR_BIN}" ]; then
  cat >"$OUT_MD" <<EOF
# Intake Gate Taylor Autopost

- posted: \`false\`
- reason: \`taylor_binary_not_available\`
EOF
  if [ "$STRICT" = "1" ]; then
    echo "taylor_autopost=FAIL (binary not available)" >&2
    exit 1
  fi
  echo "taylor_autopost=SKIP (binary not available)"
  exit 0
fi

CONTEXT_MD="artifacts/coordination/intake_gate_daily_taylor_context.md"
python3 - "$STATUS_JSON" "$SUMMARY_MD" "$DRIFT_MD" "$TRACKER_MD" "$CONTEXT_MD" <<'PY'
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

status_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
drift_path = Path(sys.argv[3])
tracker_path = Path(sys.argv[4])
context_path = Path(sys.argv[5])

status = {}
if status_path.exists():
    try:
        obj = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            status = obj
    except json.JSONDecodeError:
        status = {}

try:
    commit_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit_sha = "unknown"

lines = [
    "# Intake Gate QA + Context",
    "",
    f"- commit_sha: `{commit_sha}`",
    f"- timestamp_utc: `{status.get('timestamp_utc')}`",
    f"- milestone: `{status.get('milestone', 'M-5')}`",
    f"- contract_ok: `{status.get('contract_ok')}`",
    f"- status_contract_ok: `{status.get('status_contract_ok')}`",
    f"- drift_ok: `{status.get('drift_ok')}`",
    f"- consecutive_greens: `{status.get('consecutive_greens')}`",
    f"- close_ready: `{status.get('m5_close_ready_3_consecutive_greens')}`",
    f"- escalation: `{status.get('escalation')}`",
    "",
    "## Source Artifacts",
    f"- status_json: `{status_path.resolve()}`",
    f"- summary_md: `{summary_path.resolve()}`",
    f"- drift_md: `{drift_path.resolve()}`",
    f"- tracker_md: `{tracker_path.resolve()}`",
]

context_path.parent.mkdir(parents=True, exist_ok=True)
context_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

PROMPT='Create a concise QA + Context note for this intake gate run. Include: status verdict, policy/drift alignment, key risks (if any), and suggested PR/commit context bullets for historical continuity. Keep to 8 bullets max.'
set +e
TAYLOR_OUT="$("$TAYLOR_BIN" ask "$PROMPT" --context "$CONTEXT_MD" 2>&1)"
RC="$?"
set -e

if [ "$RC" -ne 0 ]; then
  cat >"$OUT_MD" <<EOF
# Intake Gate Taylor Autopost

- posted: \`false\`
- reason: \`taylor_ask_failed\`

## stderr/stdout

\`\`\`
$TAYLOR_OUT
\`\`\`
EOF
  if [ "$STRICT" = "1" ]; then
    echo "taylor_autopost=FAIL (ask failed)" >&2
    exit 1
  fi
  echo "taylor_autopost=SKIP (ask failed)"
  exit 0
fi

cat >"$OUT_MD" <<EOF
# Intake Gate Taylor Autopost

- posted: \`true\`
- taylor_bin: \`$TAYLOR_BIN\`
- context_file: \`$CONTEXT_MD\`

## Taylor Output

\`\`\`
$TAYLOR_OUT
\`\`\`
EOF

echo "taylor_autopost=OK"
