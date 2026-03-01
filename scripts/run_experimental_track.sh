#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
QUIET="${QUIET:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

run_cmd() {
  if [ "$QUIET" = "1" ]; then
    "$@" >/tmp/experimental_track.log 2>&1
  else
    "$@"
  fi
}

if /usr/bin/python3 - <<'PY' >/dev/null 2>&1
import socket
socket.getaddrinfo("www.youtube.com", 443)
PY
then
  run_cmd bash "$SCRIPT_DIR/experimental_weekly_ctl.sh" collect --show "$SHOW_KEY"
else
  echo "WARN: youtube DNS unavailable; collect will skip discover and use local snapshot fallback." >&2
  run_cmd env EXPERIMENTAL_SKIP_DISCOVER=1 bash "$SCRIPT_DIR/experimental_weekly_ctl.sh" collect --show "$SHOW_KEY"
fi
run_cmd bash "$SCRIPT_DIR/experimental_weekly_ctl.sh" process --show "$SHOW_KEY"
bash "$SCRIPT_DIR/print_show_contract.sh" "$SHOW_KEY"
