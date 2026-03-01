#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.deck_state import is_consumed, load_deck_state, mark_consumed
from bitpod.indexer import canonical_episode_id, load_processed


def cmd_check(args: argparse.Namespace) -> int:
    consumed = is_consumed(args.deck_id, args.sector_feed_id, args.feed_episode_id)
    print("consumed=true" if consumed else "consumed=false")
    return 0


def cmd_mark(args: argparse.Namespace) -> int:
    payload = mark_consumed(args.deck_id, args.sector_feed_id, args.feed_episode_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_pending(args: argparse.Namespace) -> int:
    state = load_deck_state()
    consumed = (
        (((state.get("decks") or {}).get(args.deck_id) or {}).get(args.sector_feed_id) or {}).get("consumed_feed_episode_ids") or []
    )
    consumed_set = set(consumed)
    index = load_processed()
    prefix = f"{args.sector_feed_id}::"
    rows = []
    for key, payload in (index.get("episodes") or {}).items():
        if not str(key).startswith(prefix):
            continue
        if payload.get("status") != "ok":
            continue
        feed_episode_id = str(payload.get("feed_episode_id") or payload.get("source_episode_id") or str(key).split("::", 1)[1])
        if feed_episode_id in consumed_set:
            continue
        rows.append(
            {
                "feed_episode_id": feed_episode_id,
                "canonical_episode_id": payload.get("canonical_episode_id") or canonical_episode_id(args.sector_feed_id, feed_episode_id),
                "published_at": payload.get("published_at"),
                "source_url": payload.get("source_url"),
            }
        )
    rows.sort(key=lambda item: str(item.get("published_at") or ""))
    print(json.dumps({"deck_id": args.deck_id, "sector_feed_id": args.sector_feed_id, "pending": rows}, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="deck_state_ctl")
    sp = p.add_subparsers(dest="cmd", required=True)

    check = sp.add_parser("check")
    check.add_argument("--deck-id", required=True)
    check.add_argument("--sector-feed-id", required=True)
    check.add_argument("--feed-episode-id", required=True)
    check.set_defaults(func=cmd_check)

    mark = sp.add_parser("mark")
    mark.add_argument("--deck-id", required=True)
    mark.add_argument("--sector-feed-id", required=True)
    mark.add_argument("--feed-episode-id", required=True)
    mark.set_defaults(func=cmd_mark)

    pending = sp.add_parser("pending")
    pending.add_argument("--deck-id", required=True)
    pending.add_argument("--sector-feed-id", required=True)
    pending.set_defaults(func=cmd_pending)
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
