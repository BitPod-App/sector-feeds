#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <show_key> <feedback_markdown_path>"
  exit 2
fi

SHOW_KEY="$1"
FEEDBACK_PATH_INPUT="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
if [ ! -f "$FEEDBACK_PATH_INPUT" ]; then
  echo "ERROR: feedback file not found: $FEEDBACK_PATH_INPUT"
  exit 2
fi

.venv311/bin/python "$SCRIPT_DIR/bitpod_ctl.py" verify \
  --show "$SHOW_KEY" \
  --gpt-feedback-file "$FEEDBACK_PATH_INPUT" \
  --gpt-note "manual feedback recorded via record_show_gpt_feedback.sh"
