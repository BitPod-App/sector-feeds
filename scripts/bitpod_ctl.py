#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.config import load_config
from bitpod.ops import (
    maybe_trigger_bitreport,
    parse_as_of_local,
    record_gpt_feedback,
    status_payload,
    sync_missing,
    verify_payload,
)


def _resolve_show_keys(target: str) -> list[str]:
    config = load_config()
    shows = sorted(config.get("shows", {}).keys())
    if target == "all":
        return shows
    if target not in shows:
        raise KeyError(f"Unknown show key: {target}")
    return [target]


def cmd_status(args: argparse.Namespace) -> int:
    as_of = parse_as_of_local(args.as_of)
    show_keys = _resolve_show_keys(args.show)
    payload = status_payload(show_keys, as_of)

    print(f"Bitpod Status as_of_utc={payload['as_of_utc']}")
    print(f"1) feeds_ready: {'Yes' if payload['all_feeds_ready'] else 'No'}")
    print(f"2) gpt_consumed_all: {'Yes' if payload['all_gpt_consumed'] else 'No'}")
    print(
        "3) gpt-bitreport: "
        f"{payload.get('latest_gpt_bitreport_path') or 'not found'} "
        f"coverage={payload.get('latest_gpt_bitreport_coverage')}"
    )
    for item in payload["shows"]:
        print(
            f"- {item['show_key']}: ready={'Yes' if item['ready_via_permalink'] else 'No'} "
            f"gpt_consumed={'Yes' if item['gpt_consumed'] else 'No'} "
            f"gpt_checks={item['gpt_check_count']}"
        )
        if item.get("failure_reason"):
            print(f"  failure={item.get('failure_stage')}: {item.get('failure_reason')}")
        if item.get("latest_feedback_path"):
            print(f"  feedback={item['latest_feedback_path']}")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    as_of = parse_as_of_local(args.as_of)
    show_keys = _resolve_show_keys(args.show)
    result = sync_missing(
        show_keys,
        as_of,
        min_caption_words=args.min_caption_words,
        min_episode_age_minutes=args.min_episode_age_minutes,
    )
    trigger = maybe_trigger_bitreport(show_keys, args.trigger_cmd)

    post = result["post_status"]
    print(f"Bitpod Sync as_of_utc={post['as_of_utc']}")
    print(f"- synced={result['synced']} skipped={result['skipped']}")
    print(f"- all_feeds_ready={'Yes' if post['all_feeds_ready'] else 'No'}")
    print(
        f"- gpt-bitreport={post.get('latest_gpt_bitreport_path') or 'not found'} "
        f"coverage={post.get('latest_gpt_bitreport_coverage')}"
    )
    print(f"- report_triggered={'Yes' if trigger.get('triggered') else 'No'} reason={trigger.get('reason')}")
    if args.json:
        print(json.dumps({"sync": result, "trigger": trigger}, indent=2, sort_keys=True))

    # Sync now enforces the same strict verify gate by default.
    verify = verify_payload(show_keys, as_of)
    print(
        "- verify_parity_ok="
        f"{'Yes' if verify['ok'] else 'No'} "
        f"(gpt_consumed_all={'Yes' if verify['status']['all_gpt_consumed'] else 'No'})"
    )

    ok = verify["ok"]
    return 0 if ok else 1


def cmd_verify(args: argparse.Namespace) -> int:
    as_of = parse_as_of_local(args.as_of)
    show_keys = _resolve_show_keys(args.show)

    if args.gpt_feedback_file or args.gpt_note:
        if args.show == "all":
            print("When recording GPT feedback, pass a specific --show (not all).")
            return 2
        record = record_gpt_feedback(args.show, feedback_path=args.gpt_feedback_file, note=args.gpt_note)
        print(f"Recorded GPT feedback check: run_id={record.get('run_id')} consumed={record.get('consumed')}")

    payload = verify_payload(show_keys, as_of)
    status = payload["status"]
    print(f"Bitpod Verify as_of_utc={status['as_of_utc']}")
    print(f"- parity_ok={'Yes' if payload['ok'] else 'No'}")
    print(f"- feeds_ready={'Yes' if status['all_feeds_ready'] else 'No'}")
    print(f"- gpt_consumed_all={'Yes' if status['all_gpt_consumed'] else 'No'}")
    print(f"- report_covers_all={'Yes' if status['latest_gpt_bitreport_covers_all_requested_shows'] else 'No'}")
    print(f"- git_dirty={'Yes' if payload['git_dirty'] else 'No'}")
    if payload["missing_status_artifacts"]:
        print(f"- missing_status_artifacts={payload['missing_status_artifacts']}")
    for item in status["shows"]:
        print(
            f"- {item['show_key']}: ready={'Yes' if item['ready_via_permalink'] else 'No'} "
            f"gpt_consumed={'Yes' if item['gpt_consumed'] else 'No'} checks={item['gpt_check_count']}"
        )
        if item.get("latest_feedback_path"):
            print(f"  feedback={item['latest_feedback_path']}")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bitpod_ctl")
    sp = p.add_subparsers(dest="cmd", required=True)

    status = sp.add_parser("status")
    status.add_argument("--show", default="all")
    status.add_argument("--as-of", default=None, help="Optional: YYYY-MM-DD[ HH:MM] in America/Managua")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    sync = sp.add_parser("sync")
    sync.add_argument("--show", default="all")
    sync.add_argument("--as-of", default=None, help="Optional: YYYY-MM-DD[ HH:MM] in America/Managua")
    sync.add_argument("--min-caption-words", type=int, default=120)
    sync.add_argument("--min-episode-age-minutes", type=int, default=180)
    sync.add_argument("--trigger-cmd", default=None, help="Optional command to regenerate gpt-bitreport when coverage is missing")
    sync.add_argument("--json", action="store_true")
    sync.set_defaults(func=cmd_sync)

    verify = sp.add_parser("verify")
    verify.add_argument("--show", default="all")
    verify.add_argument("--as-of", default=None, help="Optional: YYYY-MM-DD[ HH:MM] in America/Managua")
    verify.add_argument("--gpt-feedback-file", default=None)
    verify.add_argument("--gpt-note", default=None)
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=cmd_verify)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
