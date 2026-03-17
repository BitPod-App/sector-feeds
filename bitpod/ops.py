from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from bitpod.config import load_config
from bitpod.feeds import parse_feed
from bitpod.indexer import episode_key, load_processed, now_iso
from bitpod.paths import ROOT, resolve_repo_path
from bitpod.sync import _choose_best_source, get_feed_urls, sync_show

LOCAL_TZ = ZoneInfo("America/Managua")
REPORT_DIR = ROOT / "artifacts" / "gpt-bitreports"
FEEDBACK_DIR = ROOT / "artifacts" / "gpt-feedback"
REPORT_PATTERN = re.compile(r"gpt-bitreport-pods-(all|partial|none)-([0-9]{8}-[0-9]{4})\.md$")


@dataclass
class ShowState:
    show_key: str
    stable_pointer: str
    status_json: Path
    status_md: Path
    gpt_review_request: Path
    latest_episode_guid: str | None
    latest_episode_title: str | None
    latest_episode_published_at_utc: str | None
    latest_transcribed_ready: bool
    pointer_path: Path
    pointer_exists: bool
    run_id: str | None
    run_status: str | None
    failure_reason: str | None
    failure_stage: str | None


def parse_as_of_local(value: str | None) -> datetime:
    if not value:
        return datetime.now(LOCAL_TZ).astimezone(timezone.utc)

    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=23, minute=59)
            return parsed.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)
        except ValueError:
            continue
    raise ValueError("as_of must be 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' in America/Managua local time")


def _stable_pointer(show: dict[str, Any], show_key: str) -> str:
    configured = show.get("stable_pointer")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    return "jack_mallers.md" if show_key == "jack_mallers_show" else "latest_bitpod.md"


def _status_paths(show_key: str, stable_pointer: str) -> tuple[Path, Path, Path]:
    stem = Path(stable_pointer).stem
    show_dir = ROOT / "transcripts" / show_key
    return (
        show_dir / f"{stem}_status.json",
        show_dir / f"{stem}_status.md",
        show_dir / f"{stem}_gpt_review_request.md",
    )


def _latest_episode_for_show(show: dict[str, Any], as_of_utc: datetime) -> Any | None:
    feed_urls = get_feed_urls(show)
    episodes: list[Any] = []
    for url in feed_urls:
        episodes.extend(parse_feed(url))

    deduped: dict[str, Any] = {}
    for ep in episodes:
        if ep.published_at > as_of_utc:
            continue
        guid = str(ep.guid)
        cur = deduped.get(guid)
        deduped[guid] = ep if cur is None else _choose_best_source(cur, ep)

    if not deduped:
        return None
    return max(deduped.values(), key=lambda ep: ep.published_at)


def build_show_state(show_key: str, as_of_utc: datetime) -> ShowState:
    config = load_config()
    show = config["shows"][show_key]
    stable_pointer = _stable_pointer(show, show_key)
    status_json, status_md, gpt_review_request = _status_paths(show_key, stable_pointer)

    latest = _latest_episode_for_show(show, as_of_utc)
    index = load_processed()

    latest_ready = False
    run_id = None
    run_status = None
    failure_reason = None
    failure_stage = None

    payload: dict[str, Any] = {}
    if status_json.exists():
        payload = json.loads(status_json.read_text(encoding="utf-8"))
        run_id = payload.get("run_id")
        run_status = payload.get("run_status")
        failure_reason = payload.get("failure_reason")
        failure_stage = payload.get("failure_stage")

    if latest is not None:
        key = episode_key(show_key, latest.guid)
        existing = index.get("episodes", {}).get(key, {})
        transcript_path = existing.get("transcript_path")
        resolved = resolve_repo_path(transcript_path if isinstance(transcript_path, str) else None, root=ROOT)
        latest_ready = bool(existing.get("status") == "ok" and resolved and resolved.exists())
    else:
        # If feed lookup is temporarily unavailable, trust last successful pointer status artifact.
        latest_ready = bool(
            payload.get("run_status") == "ok"
            and payload.get("included_in_pointer") is True
            and (ROOT / "transcripts" / show_key / stable_pointer).exists()
        )

    pointer_path = ROOT / "transcripts" / show_key / stable_pointer
    return ShowState(
        show_key=show_key,
        stable_pointer=stable_pointer,
        status_json=status_json,
        status_md=status_md,
        gpt_review_request=gpt_review_request,
        latest_episode_guid=str(latest.guid) if latest else None,
        latest_episode_title=latest.title if latest else None,
        latest_episode_published_at_utc=latest.published_at.isoformat() if latest else None,
        latest_transcribed_ready=latest_ready,
        pointer_path=pointer_path,
        pointer_exists=pointer_path.exists(),
        run_id=run_id,
        run_status=run_status,
        failure_reason=failure_reason,
        failure_stage=failure_stage,
    )


def _feedback_log_path(show_key: str) -> Path:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    return FEEDBACK_DIR / f"{show_key}_consumption_log.jsonl"


def record_gpt_feedback(show_key: str, feedback_path: str | None = None, note: str | None = None) -> dict[str, Any]:
    state = build_show_state(show_key, parse_as_of_local(None))
    entry = {
        "checked_at_utc": now_iso(),
        "show_key": show_key,
        "run_id": state.run_id,
        "consumed": True,
        "feedback_path": str(Path(feedback_path).expanduser().resolve()) if feedback_path else None,
        "note": note,
    }
    path = _feedback_log_path(show_key)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def gpt_consumption_summary(show_key: str, run_id: str | None) -> dict[str, Any]:
    path = _feedback_log_path(show_key)
    if not path.exists():
        return {"consumed": False, "count": 0, "latest_feedback_path": None, "latest_note": None}

    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    count = len(lines)
    latest = lines[-1] if lines else {}
    consumed = bool(run_id and any(item.get("run_id") == run_id and item.get("consumed") for item in lines))
    return {
        "consumed": consumed,
        "count": count,
        "latest_feedback_path": latest.get("feedback_path"),
        "latest_note": latest.get("note"),
    }


def _latest_report() -> tuple[Path | None, str | None]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = sorted([p for p in REPORT_DIR.glob("gpt-bitreport-pods-*.md") if p.is_file()], key=lambda p: p.stat().st_mtime)
    if not reports:
        return None, None
    latest = reports[-1]
    m = REPORT_PATTERN.search(latest.name)
    coverage = m.group(1) if m else None
    return latest, coverage


def report_includes_show(report_path: Path | None, show_key: str) -> bool:
    if report_path is None or not report_path.exists():
        return False
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    needle = show_key.lower()
    if needle in text.lower():
        return True
    marker = f"included_shows: {show_key}"
    return marker.lower() in text.lower()


def status_payload(show_keys: list[str], as_of_utc: datetime) -> dict[str, Any]:
    shows: list[dict[str, Any]] = []
    all_ready = True
    all_consumed = True

    latest_report_path, latest_report_coverage = _latest_report()

    for show_key in show_keys:
        state = build_show_state(show_key, as_of_utc)
        gpt = gpt_consumption_summary(show_key, state.run_id)
        included_in_report = report_includes_show(latest_report_path, show_key)
        ready = state.latest_transcribed_ready and state.pointer_exists
        all_ready = all_ready and ready
        all_consumed = all_consumed and bool(gpt["consumed"])
        shows.append(
            {
                "show_key": show_key,
                "latest_episode_title": state.latest_episode_title,
                "latest_episode_guid": state.latest_episode_guid,
                "latest_episode_published_at_utc": state.latest_episode_published_at_utc,
                "ready_via_permalink": ready,
                "pointer_path": str(state.pointer_path),
                "run_status": state.run_status,
                "run_id": state.run_id,
                "failure_stage": state.failure_stage,
                "failure_reason": state.failure_reason,
                "gpt_consumed": bool(gpt["consumed"]),
                "gpt_check_count": gpt["count"],
                "latest_feedback_path": gpt["latest_feedback_path"],
                "latest_feedback_note": gpt["latest_note"],
                "status_json": str(state.status_json),
                "status_md": str(state.status_md),
                "gpt_review_request": str(state.gpt_review_request),
                "latest_report_includes_show": included_in_report,
            }
        )

    coverage_all = latest_report_coverage == "all" and all(item["latest_report_includes_show"] for item in shows)
    return {
        "as_of_utc": as_of_utc.isoformat(),
        "all_feeds_ready": all_ready,
        "all_gpt_consumed": all_consumed,
        "shows": shows,
        "latest_gpt_bitreport_path": str(latest_report_path) if latest_report_path else None,
        "latest_gpt_bitreport_coverage": latest_report_coverage,
        "latest_gpt_bitreport_covers_all_requested_shows": coverage_all,
    }


def sync_missing(
    show_keys: list[str],
    as_of_utc: datetime,
    min_caption_words: int = 120,
    min_episode_age_minutes: int = 180,
) -> dict[str, Any]:
    config = load_config()
    synced: list[str] = []
    skipped: list[str] = []

    for show_key in show_keys:
        state_before = build_show_state(show_key, as_of_utc)
        if state_before.latest_transcribed_ready and state_before.pointer_exists:
            skipped.append(show_key)
            continue

        show = config["shows"][show_key]
        sync_show(
            show=show,
            max_episodes=1,
            source_policy="balanced",
            min_caption_words=min_caption_words,
            min_episode_age_minutes=min_episode_age_minutes,
            as_of_utc=as_of_utc,
        )
        synced.append(show_key)

    return {
        "synced": synced,
        "skipped": skipped,
        "post_status": status_payload(show_keys, as_of_utc),
    }


def maybe_trigger_bitreport(show_keys: list[str], trigger_cmd: str | None) -> dict[str, Any]:
    latest_report_path, coverage = _latest_report()
    coverage_ok = coverage == "all" and all(report_includes_show(latest_report_path, key) for key in show_keys)
    if coverage_ok:
        return {"triggered": False, "reason": "already_all", "report_path": str(latest_report_path) if latest_report_path else None}

    if not trigger_cmd:
        return {"triggered": False, "reason": "missing_trigger_cmd", "report_path": str(latest_report_path) if latest_report_path else None}

    completed = subprocess.run(trigger_cmd, shell=True, cwd=str(ROOT), capture_output=True, text=True)
    new_report, new_cov = _latest_report()
    return {
        "triggered": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
        "report_path": str(new_report) if new_report else None,
        "report_coverage": new_cov,
    }


def verify_payload(show_keys: list[str], as_of_utc: datetime) -> dict[str, Any]:
    status = status_payload(show_keys, as_of_utc)
    git_dirty = bool(subprocess.run(["git", "status", "--short"], cwd=str(ROOT), capture_output=True, text=True).stdout.strip())

    missing_status = []
    for item in status["shows"]:
        if not Path(item["status_json"]).exists() or not Path(item["status_md"]).exists():
            missing_status.append(item["show_key"])

    ok = (
        status["all_feeds_ready"]
        and status["all_gpt_consumed"]
        and status["latest_gpt_bitreport_covers_all_requested_shows"]
        and not missing_status
    )

    return {
        "ok": ok,
        "status": status,
        "git_dirty": git_dirty,
        "missing_status_artifacts": missing_status,
    }
