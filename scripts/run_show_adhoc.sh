#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key> [min_caption_words] [min_episode_age_minutes]"
  exit 2
fi

SHOW_KEY="$1"
MIN_CAPTION_WORDS="${2:-${MIN_CAPTION_WORDS:-120}}"
MIN_EPISODE_AGE_MINUTES="${3:-${MIN_EPISODE_AGE_MINUTES:-180}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Preflight check: if latest selected episode is already OK, do not run sync.
if .venv311/bin/python - "$SHOW_KEY" <<'PY'
import json
import sys
from pathlib import Path

from bitpod.config import get_show, load_config
from bitpod.feeds import parse_feed
from bitpod.indexer import episode_key, load_processed
from bitpod.sync import _choose_best_source, filter_episodes, get_feed_urls

show_key = sys.argv[1]
config = load_config()
show = get_show(config, show_key)
feed_urls = get_feed_urls(show)
if not feed_urls:
    print("NEED_SYNC:no_feeds")
    raise SystemExit(1)

episodes = []
for url in feed_urls:
    episodes.extend(parse_feed(url))

deduped = {}
for ep in episodes:
    guid = str(ep.guid)
    cur = deduped.get(guid)
    deduped[guid] = ep if cur is None else _choose_best_source(cur, ep)

selected = filter_episodes(list(deduped.values()), max_episodes=1)
if not selected:
    print("UP_TO_DATE:no_selected_episodes")
    raise SystemExit(0)

latest = selected[0]
index = load_processed()
key = episode_key(show_key, latest.guid)
existing = index.get("episodes", {}).get(key, {})
status = existing.get("status")
path = existing.get("transcript_path")
if status == "ok" and isinstance(path, str) and path and Path(path).exists():
    print(f"UP_TO_DATE:{latest.title}")
    raise SystemExit(0)

print(f"NEED_SYNC:{latest.title}")
raise SystemExit(1)
PY
then
  echo "Ad hoc sync skipped: latest selected episode already processed."
  exit 0
fi

# Not up-to-date, run full weekly flow for this show.
"$SCRIPT_DIR/run_show_weekly.sh" "$SHOW_KEY" "$MIN_CAPTION_WORDS" "$MIN_EPISODE_AGE_MINUTES"
