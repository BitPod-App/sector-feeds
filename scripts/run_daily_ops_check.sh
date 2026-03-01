#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CONTRACT_JSON="$(bash "$SCRIPT_DIR/print_show_contract.sh" "$SHOW_KEY" --json)"
if bash "$SCRIPT_DIR/check_track_status_board.sh" "$SHOW_KEY" >/tmp/track_status_check_${SHOW_KEY}.log 2>&1; then
  TRACK_STATUS="PASS"
else
  TRACK_STATUS="FAIL"
fi

echo "show_key=$SHOW_KEY track_status=$TRACK_STATUS"
echo "$CONTRACT_JSON"
echo "track_status_check_log=/tmp/track_status_check_${SHOW_KEY}.log"

if [ "$TRACK_STATUS" != "PASS" ]; then
  exit 1
fi

