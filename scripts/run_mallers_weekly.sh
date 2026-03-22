#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHOW_KEY="jack_mallers_show"
TRACK_NAME="${BITPOD_TRACK_NAME:-mallers_weekly_fetch}"
FEED_MODE="${BITPOD_FEED_MODE:-all}"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv311/bin/python"
: "${WEEKLY_GPT_REPORT:=0}"
export WEEKLY_GPT_REPORT

set +e
bash "$SCRIPT_DIR/run_show_weekly.sh" "$SHOW_KEY" "$@"
run_exit=$?
set -e

"$PYTHON_BIN" "$SCRIPT_DIR/render_weekly_run_summary.py" --show "$SHOW_KEY" --track "$TRACK_NAME" --feed-mode "$FEED_MODE"
exit "$run_exit"
