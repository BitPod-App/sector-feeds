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

# Lowest-cost Tuesday path: never trigger network/discovery/sync work.
# This command evaluates current local readiness only.
run_cmd bash "$SCRIPT_DIR/report_show_weekly_status.sh" "$SHOW_KEY" tuesday
bash "$SCRIPT_DIR/print_show_contract.sh" "$SHOW_KEY"
