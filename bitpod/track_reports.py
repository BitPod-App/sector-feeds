from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitpod.ops import parse_as_of_local, status_payload
from bitpod.paths import ROOT


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_slug(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_output_dir(track_name: str, show_key: str) -> Path:
    return ROOT / "artifacts" / "runs" / track_name / show_key


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _experimental_snapshot(show_key: str) -> dict[str, Any]:
    return _load_json(ROOT / "artifacts" / "private" / "experimental_weekly" / f"{show_key}_intake_snapshot.json")


def _weekly_gate_payload() -> dict[str, Any]:
    return _load_json(
        ROOT.parent / "bitregime-core" / "artifacts" / "gates" / "weekly_bundle_gate_status.json"
    )


def build_track_run_summary(show_key: str, track_name: str, feed_mode: str) -> dict[str, Any]:
    generated_at = _utc_now()
    payload = status_payload([show_key], parse_as_of_local(None))
    show = (payload.get("shows") or [{}])[0]
    status_json_path = Path(show["status_json"]) if show.get("status_json") else None
    raw_status = _load_json(status_json_path)
    experimental_snapshot = _experimental_snapshot(show_key)
    gate_payload = _weekly_gate_payload()

    shared_permalink = {
        "transcript_url": raw_status.get("public_permalink_transcript_url"),
        "status_url": raw_status.get("public_permalink_status_url"),
        "discovery_url": raw_status.get("public_permalink_discovery_url"),
    }
    permalink_paths = {
        "status_json": raw_status.get("public_permalink_status_path"),
        "transcript_md": raw_status.get("public_permalink_transcript_path"),
        "intake_md": raw_status.get("public_permalink_intake_path"),
        "discovery_json": raw_status.get("public_permalink_discovery_path"),
    }
    permalink_ready = all(bool(v) for v in shared_permalink.values())

    summary = {
        "contract_version": "track_run_summary.v1",
        "generated_at_utc": generated_at.isoformat(),
        "track_name": track_name,
        "show_key": show_key,
        "feed_mode_effective": feed_mode,
        "latest_episode_guid": show.get("latest_episode_guid"),
        "latest_episode_title": show.get("latest_episode_title"),
        "latest_episode_published_at_utc": show.get("latest_episode_published_at_utc"),
        "source_platform": raw_status.get("source_platform")
        or raw_status.get("transcript_source_type")
        or raw_status.get("attempted_source_type"),
        "source_url": raw_status.get("source_url")
        or raw_status.get("transcript_source_url")
        or raw_status.get("attempted_source_url")
        or raw_status.get("episode_url"),
        "source_episode_id": raw_status.get("source_episode_id")
        or raw_status.get("episode_guid")
        or raw_status.get("latest_episode_guid"),
        "canonical_episode_id": raw_status.get("canonical_episode_id")
        or raw_status.get("episode_guid")
        or raw_status.get("latest_episode_guid"),
        "run_id": show.get("run_id"),
        "run_status": show.get("run_status"),
        "processed_successfully": show.get("run_status") == "ok",
        "new_episode_detected": bool(raw_status.get("new_episode_detected")),
        "included_in_pointer": bool(raw_status.get("included_in_pointer")),
        "ready_via_permalink": bool(show.get("ready_via_permalink")),
        "transcript_quality_state": raw_status.get("transcript_quality_state"),
        "permalink_ready": permalink_ready,
        "shared_permalink_contract": shared_permalink,
        "shared_permalink_paths": permalink_paths,
        "gpt_consumed": bool(show.get("gpt_consumed")),
        "gpt_check_count": int(show.get("gpt_check_count") or 0),
        "latest_feedback_path": show.get("latest_feedback_path"),
        "latest_feedback_note": show.get("latest_feedback_note"),
        "latest_gpt_bitreport_path": payload.get("latest_gpt_bitreport_path"),
        "latest_gpt_bitreport_coverage": payload.get("latest_gpt_bitreport_coverage"),
        "latest_report_includes_show": bool(show.get("latest_report_includes_show")),
        "gpt_review_request_path": show.get("gpt_review_request"),
        "status_json_path": show.get("status_json"),
        "status_md_path": show.get("status_md"),
        "plain_artifact_path": raw_status.get("plain_artifact_path"),
        "segments_artifact_path": raw_status.get("segments_artifact_path"),
        "failure_stage": raw_status.get("failure_stage"),
        "failure_reason": raw_status.get("failure_reason"),
        "suggested_next_action": raw_status.get("suggested_next_action"),
        "experimental_snapshot_path": str(ROOT / "artifacts" / "private" / "experimental_weekly" / f"{show_key}_intake_snapshot.json"),
        "experimental_snapshot_contract_ready": bool(
            (experimental_snapshot.get("shared_permalink_contract") or {}).get("public_permalink_transcript_url")
            and (experimental_snapshot.get("shared_permalink_contract") or {}).get("public_permalink_status_url")
            and (experimental_snapshot.get("shared_permalink_contract") or {}).get("public_permalink_discovery_url")
        ),
        "weekly_gate_path": str(ROOT.parent / "bitregime-core" / "artifacts" / "gates" / "weekly_bundle_gate_status.json"),
        "weekly_gate_status": gate_payload.get("gate_status"),
    }

    if track_name == "legacy_tuesday_track":
        summary["track_purpose"] = "lightweight Tuesday readiness + GPT usage proof"
        summary["success"] = all(
            [
                summary["processed_successfully"],
                summary["included_in_pointer"],
                summary["ready_via_permalink"],
                summary["permalink_ready"],
                summary["gpt_consumed"],
                summary["latest_report_includes_show"],
            ]
        )
    elif track_name == "mallers_weekly_fetch":
        summary["track_purpose"] = "active Monday fetch automation for transcript/status/permalink refresh"
        summary["success"] = all(
            [
                summary["processed_successfully"],
                summary["included_in_pointer"],
                summary["ready_via_permalink"],
                summary["permalink_ready"],
            ]
        )
    else:
        summary["track_purpose"] = "diff/evaluation lane with intake snapshot + optional weekly gate"
        summary["success"] = all(
            [
                summary["processed_successfully"],
                summary["included_in_pointer"],
                summary["ready_via_permalink"],
                summary["permalink_ready"],
            ]
        )
    return summary


def write_track_run_summary(show_key: str, track_name: str, feed_mode: str) -> tuple[Path, Path, dict[str, Any]]:
    summary = build_track_run_summary(show_key=show_key, track_name=track_name, feed_mode=feed_mode)
    timestamp = _timestamp_slug(datetime.fromisoformat(summary["generated_at_utc"]))
    out_dir = _run_output_dir(track_name, show_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{timestamp}__summary.md"
    json_path = out_dir / f"{timestamp}__status.json"

    lines = [
        f"# Weekly Track Summary: {track_name}",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- show_key: `{show_key}`",
        f"- feed_mode_effective: `{feed_mode}`",
        f"- track_purpose: `{summary['track_purpose']}`",
        f"- success: `{summary['success']}`",
        "",
        "## Latest Episode",
        f"- latest_episode_guid: `{summary.get('latest_episode_guid')}`",
        f"- latest_episode_title: `{summary.get('latest_episode_title')}`",
        f"- latest_episode_published_at_utc: `{summary.get('latest_episode_published_at_utc')}`",
        f"- source_platform: `{summary.get('source_platform')}`",
        f"- source_url: `{summary.get('source_url')}`",
        f"- source_episode_id: `{summary.get('source_episode_id')}`",
        "",
        "## Run Outcome",
        f"- run_id: `{summary.get('run_id')}`",
        f"- run_status: `{summary.get('run_status')}`",
        f"- processed_successfully: `{summary.get('processed_successfully')}`",
        f"- new_episode_detected: `{summary.get('new_episode_detected')}`",
        f"- included_in_pointer: `{summary.get('included_in_pointer')}`",
        f"- ready_via_permalink: `{summary.get('ready_via_permalink')}`",
        f"- transcript_quality_state: `{summary.get('transcript_quality_state')}`",
        f"- permalink_ready: `{summary.get('permalink_ready')}`",
        f"- failure_stage: `{summary.get('failure_stage')}`",
        f"- failure_reason: `{summary.get('failure_reason')}`",
        f"- suggested_next_action: `{summary.get('suggested_next_action')}`",
        "",
        "## GPT / App Consumption",
        f"- gpt_consumed: `{summary.get('gpt_consumed')}`",
        f"- gpt_check_count: `{summary.get('gpt_check_count')}`",
        f"- latest_feedback_path: `{summary.get('latest_feedback_path')}`",
        f"- latest_feedback_note: `{summary.get('latest_feedback_note')}`",
        f"- latest_gpt_bitreport_path: `{summary.get('latest_gpt_bitreport_path')}`",
        f"- latest_gpt_bitreport_coverage: `{summary.get('latest_gpt_bitreport_coverage')}`",
        f"- latest_report_includes_show: `{summary.get('latest_report_includes_show')}`",
        "",
        "## Shared Permalink Contract",
        f"- transcript_url: `{summary['shared_permalink_contract'].get('transcript_url')}`",
        f"- status_url: `{summary['shared_permalink_contract'].get('status_url')}`",
        f"- discovery_url: `{summary['shared_permalink_contract'].get('discovery_url')}`",
        f"- status_json_path: `{summary['shared_permalink_paths'].get('status_json')}`",
        f"- transcript_md_path: `{summary['shared_permalink_paths'].get('transcript_md')}`",
        f"- intake_md_path: `{summary['shared_permalink_paths'].get('intake_md')}`",
        f"- discovery_json_path: `{summary['shared_permalink_paths'].get('discovery_json')}`",
        "",
        "## Related Artifacts",
        f"- gpt_review_request_path: `{summary.get('gpt_review_request_path')}`",
        f"- status_json_path: `{summary.get('status_json_path')}`",
        f"- status_md_path: `{summary.get('status_md_path')}`",
        f"- plain_artifact_path: `{summary.get('plain_artifact_path')}`",
        f"- segments_artifact_path: `{summary.get('segments_artifact_path')}`",
        f"- experimental_snapshot_path: `{summary.get('experimental_snapshot_path')}`",
        f"- experimental_snapshot_contract_ready: `{summary.get('experimental_snapshot_contract_ready')}`",
        f"- weekly_gate_path: `{summary.get('weekly_gate_path')}`",
        f"- weekly_gate_status: `{summary.get('weekly_gate_status')}`",
    ]

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return md_path, json_path, summary
