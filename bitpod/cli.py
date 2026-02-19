from __future__ import annotations

import argparse
import json
import logging

from bitpod.config import get_show, load_config, save_config
from bitpod.discovery import discover_show_feeds
from bitpod.sync import sync_show


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _cmd_discover(args: argparse.Namespace) -> int:
    config = load_config()
    show = get_show(config, args.show)
    feeds = discover_show_feeds(show)
    show["feeds"] = feeds
    save_config(config)
    print(json.dumps({"show": args.show, "feeds": feeds}, indent=2))
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    config = load_config()
    show = get_show(config, args.show)
    stats = sync_show(
        show,
        model=args.model,
        max_episodes=args.max_episodes,
        since_days=args.since_days,
        dry_run=args.dry_run,
        source_policy=args.source_policy,
        no_youtube_download=args.no_youtube_download,
        min_caption_words=args.min_caption_words,
    )
    print(json.dumps({"show": args.show, "stats": stats}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bitpod", description="Podcast to transcript pipeline")
    parser.add_argument("--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Discover RSS feeds for a show")
    discover_parser.add_argument("--show", required=True)
    discover_parser.set_defaults(func=_cmd_discover)

    sync_parser = subparsers.add_parser("sync", help="Sync episodes and transcripts for a show")
    sync_parser.add_argument("--show", required=True)
    sync_parser.add_argument("--model", default="gpt-4o-mini-transcribe")
    sync_parser.add_argument("--max-episodes", type=int, default=3)
    sync_parser.add_argument("--since-days", type=int)
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument(
        "--source-policy",
        choices=["audio-first", "balanced", "caption-first", "media-first"],
        default="balanced",
        help="How aggressively to favor captions/audio before media downloads",
    )
    sync_parser.add_argument(
        "--no-youtube-download",
        action="store_true",
        help="Fail instead of downloading YouTube media when captions are unavailable or low quality",
    )
    sync_parser.add_argument(
        "--min-caption-words",
        type=int,
        default=120,
        help="Minimum caption word count required before using caption text as transcript",
    )
    sync_parser.set_defaults(func=_cmd_sync)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    return args.func(args)
