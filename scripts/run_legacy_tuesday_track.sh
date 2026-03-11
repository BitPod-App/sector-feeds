#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
QUIET="${QUIET:-0}"
BITPOD_FEED_MODE="${BITPOD_FEED_MODE:-rss_preferred}"
WEEKLY_GPT_REPORT="${WEEKLY_GPT_REPORT:-1}"
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

if ! run_cmd env BITPOD_FEED_MODE="$BITPOD_FEED_MODE" WEEKLY_GPT_REPORT="$WEEKLY_GPT_REPORT" bash "$SCRIPT_DIR/run_show_weekly.sh" "$SHOW_KEY"; then
  echo "WARN: run_show_weekly failed; continuing with latest available status artifacts." >&2
fi
run_cmd bash "$SCRIPT_DIR/report_show_weekly_status.sh" "$SHOW_KEY" tuesday
python3 "$SCRIPT_DIR/render_weekly_run_summary.py" --show "$SHOW_KEY" --track legacy_tuesday_track --feed-mode "$BITPOD_FEED_MODE"
bash "$SCRIPT_DIR/print_show_contract.sh" "$SHOW_KEY"
