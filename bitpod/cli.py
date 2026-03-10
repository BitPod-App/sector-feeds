from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from bitpod.config import get_show, load_config, save_config
from bitpod.paths import RETRO_FLAG_QUEUE_PATH


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _cmd_discover(args: argparse.Namespace) -> int:
    from bitpod.discovery import discover_show_feeds

    config = load_config()
    show = get_show(config, args.show)
    feeds = discover_show_feeds(show)
    show["feeds"] = feeds
    save_config(config)
    print(json.dumps({"show": args.show, "feeds": feeds}, indent=2))
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    from bitpod.sync import sync_show

    config = load_config()
    show = get_show(config, args.show)
    stats = sync_show(
        show,
        model=args.model,
        max_episodes=args.max_episodes,
        since_days=args.since_days,
        dry_run=args.dry_run,
        feed_mode=args.feed_mode,
        source_policy=args.source_policy,
        no_youtube_download=args.no_youtube_download,
        min_caption_words=args.min_caption_words,
        min_episode_age_minutes=args.min_episode_age_minutes,
    )
    print(json.dumps({"show": args.show, "stats": stats}, indent=2))
    return 0


def _cmd_retro_flags(args: argparse.Namespace) -> int:
    from bitpod.retro_flags import load_flag_entries, summarize_flag_entries

    try:
        path = Path(args.path).expanduser() if args.path else RETRO_FLAG_QUEUE_PATH
        entries = load_flag_entries(path=path)
        summary = summarize_flag_entries(entries, limit=args.limit)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    payload = {"path": str(path), **summary}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(
        "retrospective_flags "
        f"path={path} total={summary['total']} open={summary['open']} closed={summary['closed']}"
    )
    for entry in summary["recent"]:
        print(
            "- "
            f"{entry.get('created_at_utc', '?')} "
            f"id={entry.get('id', '?')} "
            f"status={entry.get('status', '?')} "
            f"scope={entry.get('scope', '?')} "
            f"source={entry.get('source', '?')} "
            f"run_id={entry.get('run_id', '')} "
            f"note={entry.get('note', '')}"
        )
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
        "--feed-mode",
        choices=["all", "rss_preferred", "rss_only"],
        default="all",
        help="Which feed sources are eligible for this run",
    )
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
        help="Minimum stitched caption words required before captions are accepted",
    )
    sync_parser.add_argument(
        "--min-episode-age-minutes",
        type=int,
        default=180,
        help="Skip very recent YouTube/live episodes until they are at least this old",
    )
    sync_parser.set_defaults(func=_cmd_sync)

    retro_flags_parser = subparsers.add_parser(
        "retro-flags", help="Summarize retrospective flag queue for meeting prep"
    )
    retro_flags_parser.add_argument("--limit", type=int, default=10, help="Number of recent items to show")
    retro_flags_parser.add_argument(
        "--json", action="store_true", help="Print machine-readable summary JSON"
    )
    retro_flags_parser.add_argument(
        "--path",
        help=(
            "Optional path to retrospective flag queue JSONL "
            f"(default: {RETRO_FLAG_QUEUE_PATH})"
        ),
    )
    retro_flags_parser.set_defaults(func=_cmd_retro_flags)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    return args.func(args)
