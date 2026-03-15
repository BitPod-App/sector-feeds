#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/taylor_runtime_keepalive.sh [output_json_path]

Runs lightweight Taylor runtime health checks and writes a keepalive artifact.
Default output:
  artifacts/coordination/taylor_runtime_keepalive.json
USAGE
}

if [ "$#" -gt 1 ]; then
  usage
  exit 2
fi

OUT_JSON="${1:-artifacts/coordination/taylor_runtime_keepalive.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

TAYLOR_BIN="${TAYLOR_BIN:-}"
if [[ -z "${TAYLOR_BIN}" ]] && command -v taylor >/dev/null 2>&1; then
  TAYLOR_BIN="$(command -v taylor)"
fi

timestamp_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
mkdir -p "$(dirname "$OUT_JSON")"

if [ ! -x "$TAYLOR_BIN" ]; then
  cat >"$OUT_JSON" <<EOF
{
  "timestamp_utc": "$timestamp_utc",
  "keepalive_ok": false,
  "reason": "taylor_binary_not_found",
  "taylor_bin": "${TAYLOR_BIN:-unset}"
}
EOF
  echo "taylor_keepalive=SKIP (binary not found)"
  exit 0
fi

set +e
WHOAMI_OUT="$("$TAYLOR_BIN" whoami 2>&1)"
WHOAMI_RC="$?"
SELF_OUT="$("$TAYLOR_BIN" self-test --out-root /tmp 2>&1)"
SELF_RC="$?"
set -e

if [ "$WHOAMI_RC" -eq 0 ] && [ "$SELF_RC" -eq 0 ]; then
  cat >"$OUT_JSON" <<EOF
{
  "timestamp_utc": "$timestamp_utc",
  "keepalive_ok": true,
  "reason": "ok",
  "taylor_bin": "$TAYLOR_BIN"
}
EOF
  echo "taylor_keepalive=OK"
  exit 0
fi

cat >"$OUT_JSON" <<EOF
{
  "timestamp_utc": "$timestamp_utc",
  "keepalive_ok": false,
  "reason": "health_check_failed",
  "taylor_bin": "$TAYLOR_BIN",
  "whoami_rc": $WHOAMI_RC,
  "self_test_rc": $SELF_RC
}
EOF
echo "taylor_keepalive=WARN"
exit 0
