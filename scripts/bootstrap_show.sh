#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <show_key> <rss_url> <stable_pointer_md> <sector> [format_tag] [youtube_handle] [youtube_channel_id]"
  exit 2
fi

SHOW_KEY="$1"
RSS_URL="$2"
STABLE_POINTER="$3"
SECTOR="$4"
FORMAT_TAG="${5:-podcast}"
YOUTUBE_HANDLE="${6:-}"
YOUTUBE_CHANNEL_ID="${7:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" "$RSS_URL" "$STABLE_POINTER" "$SECTOR" "$FORMAT_TAG" "$YOUTUBE_HANDLE" "$YOUTUBE_CHANNEL_ID" <<'PY'
import json
import sys
from pathlib import Path

show_key, rss_url, stable_pointer, sector, format_tag, youtube_handle, youtube_channel_id = sys.argv[1:8]
path = Path("shows.json")
cfg = json.loads(path.read_text(encoding="utf-8"))
shows = cfg.setdefault("shows", {})
if show_key in shows:
    raise SystemExit(f"Show already exists: {show_key}")

entry = {
    "show_key": show_key,
    "stable_pointer": stable_pointer,
    "sector": sector,
    "series_is_feed_unit": True,
    "feed_unit_type": "series_or_playlist_or_feed",
    "format_tags": [format_tag],
    "feeds": {"rss": [rss_url]},
}
if youtube_handle:
    entry["youtube_handle"] = youtube_handle
    entry["youtube_channel_url"] = f"https://youtube.com/{youtube_handle}" if youtube_handle.startswith("@") else f"https://youtube.com/@{youtube_handle}"
if youtube_channel_id:
    entry["feeds"]["youtube_channel_id"] = youtube_channel_id
    entry["feeds"]["youtube"] = f"https://www.youtube.com/feeds/videos.xml?channel_id={youtube_channel_id}"

shows[show_key] = entry
path.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"bootstrapped_show={show_key}")
PY

echo "next_discover=.venv311/bin/python -m bitpod discover --show $SHOW_KEY"
echo "next_sync=bash scripts/run_show_weekly.sh $SHOW_KEY"
echo "next_contract=bash scripts/print_show_contract.sh $SHOW_KEY"

