#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.config import get_show, load_config
from bitpod.feeds import parse_feed
from bitpod.indexer import episode_key, load_processed
from bitpod.sync import _choose_best_source, filter_episodes, get_feed_urls


def main() -> int:
    parser = argparse.ArgumentParser(prog="track_preflight")
    parser.add_argument("--show", required=True)
    parser.add_argument("--feed-mode", choices=["all", "rss_preferred", "rss_only"], default="all")
    parser.add_argument("--max-episodes", type=int, default=1)
    args = parser.parse_args()

    config = load_config()
    show = get_show(config, args.show)
    feed_urls = get_feed_urls(show, feed_mode=args.feed_mode)
    if not feed_urls:
        print("HEAVY_WORK_REQUIRED=true")
        print("HEAVY_WORK_REASON=no_feeds")
        return 0

    episodes = []
    for url in feed_urls:
        episodes.extend(parse_feed(url))

    deduped = {}
    for ep in episodes:
        guid = str(ep.guid)
        cur = deduped.get(guid)
        deduped[guid] = ep if cur is None else _choose_best_source(cur, ep)

    selected = filter_episodes(list(deduped.values()), max_episodes=args.max_episodes)
    if not selected:
        print("HEAVY_WORK_REQUIRED=false")
        print("HEAVY_WORK_REASON=no_selected_episodes")
        return 0

    latest = selected[0]
    index = load_processed()
    key = episode_key(args.show, latest.guid)
    existing = index.get("episodes", {}).get(key, {})
    status = existing.get("status")
    path = existing.get("transcript_path")

    if status == "ok" and isinstance(path, str) and path and Path(path).exists():
        print("HEAVY_WORK_REQUIRED=false")
        print("HEAVY_WORK_REASON=latest_selected_episode_already_processed")
        print(f"LATEST_EPISODE_TITLE={json.dumps(latest.title)}")
        print(f"FEED_MODE={args.feed_mode}")
        return 0

    print("HEAVY_WORK_REQUIRED=true")
    print("HEAVY_WORK_REASON=latest_selected_episode_missing_or_not_ok")
    print(f"LATEST_EPISODE_TITLE={json.dumps(latest.title)}")
    print(f"FEED_MODE={args.feed_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
