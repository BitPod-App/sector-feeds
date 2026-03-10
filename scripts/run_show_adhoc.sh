#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key> [min_caption_words] [min_episode_age_minutes]"
  exit 2
fi

SHOW_KEY="$1"
MIN_CAPTION_WORDS="${2:-${MIN_CAPTION_WORDS:-120}}"
MIN_EPISODE_AGE_MINUTES="${3:-${MIN_EPISODE_AGE_MINUTES:-180}}"
BITPOD_FEED_MODE="${BITPOD_FEED_MODE:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

PREFLIGHT_OUTPUT="$(python3 "$SCRIPT_DIR/track_preflight.py" --show "$SHOW_KEY" --feed-mode "$BITPOD_FEED_MODE")"
printf '%s\n' "$PREFLIGHT_OUTPUT"

if printf '%s\n' "$PREFLIGHT_OUTPUT" | grep -q '^HEAVY_WORK_REQUIRED=false$'; then
  echo "Ad hoc sync skipped: latest selected episode already processed."
  exit 0
fi

# Not up-to-date, run full weekly flow for this show.
"$SCRIPT_DIR/run_show_weekly.sh" "$SHOW_KEY" "$MIN_CAPTION_WORDS" "$MIN_EPISODE_AGE_MINUTES"
