#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
QUIET="${QUIET:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

run_cmd() {
  if [ "$QUIET" = "1" ]; then
    "$@" >/tmp/legacy_tuesday_track.log 2>&1
  else
    "$@"
  fi
}

if /usr/bin/python3 - <<'PY' >/dev/null 2>&1
import socket
socket.getaddrinfo("www.youtube.com", 443)
PY
then
  if ! run_cmd bash "$SCRIPT_DIR/run_show_weekly.sh" "$SHOW_KEY"; then
    echo "WARN: run_show_weekly failed; continuing with latest available status artifacts." >&2
  fi
else
  echo "WARN: youtube DNS unavailable; skipping run_show_weekly and using latest status artifacts." >&2
fi
run_cmd bash "$SCRIPT_DIR/report_show_weekly_status.sh" "$SHOW_KEY" tuesday
bash "$SCRIPT_DIR/print_show_contract.sh" "$SHOW_KEY"
