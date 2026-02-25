from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitpod.paths import TRANSCRIPTS_ROOT

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = SLUG_PATTERN.sub("-", value.lower()).strip("-")
    return slug[:80] or "episode"


def _fmt_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def transcript_path(show_key: str, published_at: datetime, episode_title: str, root: Path = TRANSCRIPTS_ROOT) -> Path:
    year = published_at.strftime("%Y")
    date_prefix = published_at.strftime("%Y-%m-%d")
    slug = slugify(episode_title)
    return root / show_key / year / f"{date_prefix}__{slug}.md"


def write_transcript(
    *,
    show_key: str,
    episode_title: str,
    published_at: datetime,
    source_url: str,
    guid: str,
    transcript_text: str,
    transcription_model: str,
    segments: list[dict[str, Any]] | None = None,
    transcript_source: str = "audio_transcription",
    speaker_strategy: str = "guest_priority",
) -> Path:
    target = transcript_path(show_key, published_at, episode_title)
    target.parent.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(timezone.utc)
    frontmatter = {
        "show_key": show_key,
        "episode_title": episode_title,
        "published_at": _fmt_dt(published_at),
        "source_url": source_url,
        "guid": guid,
        "fetched_at": _fmt_dt(fetched_at),
        "transcription_model": transcription_model,
        "transcript_source": transcript_source,
        "speaker_strategy": speaker_strategy,
        "guest_weighting_hint": "guest_over_host",
        "speaker_segments_present": bool(segments),
    }

    lines = ["---"]
    for key, value in frontmatter.items():
        escaped = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.extend(["---", "", transcript_text.strip(), ""])

    if segments:
        lines.append("## Segments")
        for segment in segments:
            start = segment.get("start")
            end = segment.get("end")
            text = str(segment.get("text", "")).strip()
            lines.append(f"- [{start} - {end}] {text}")
        lines.append("")

    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _artifact_paths(transcript_file: Path) -> tuple[Path, Path]:
    stem = transcript_file.stem
    plain = transcript_file.with_name(f"{stem}_plain.txt")
    segments = transcript_file.with_name(f"{stem}_segments.jsonl")
    return plain, segments


def write_output_artifacts(
    *,
    transcript_file: Path,
    transcript_text: str,
    segments: list[dict[str, Any]] | None,
    metadata: dict[str, Any],
) -> tuple[Path, Path]:
    plain_path, segments_path = _artifact_paths(transcript_file)
    plain_path.parent.mkdir(parents=True, exist_ok=True)

    header = ["---"]
    for key, value in metadata.items():
        escaped = str(value).replace('"', '\\"')
        header.append(f'{key}: "{escaped}"')
    header.extend(["---", "", transcript_text.strip(), ""])
    plain_path.write_text("\n".join(header), encoding="utf-8")

    segment_rows: list[str] = []
    for segment in segments or []:
        start = segment.get("start")
        end = segment.get("end")
        text = str(segment.get("text", "")).strip()
        speaker = segment.get("speaker")
        source = segment.get("source")
        row = {
            "start": start,
            "end": end,
            "speaker": speaker,
            "text": text,
            "source": source,
        }
        segment_rows.append(json.dumps(row, ensure_ascii=False))
    segments_path.write_text("\n".join(segment_rows) + ("\n" if segment_rows else ""), encoding="utf-8")
    return plain_path, segments_path


def status_paths(show_key: str, status_basename: str = "mallers_bitpod_status") -> tuple[Path, Path]:
    base_dir = TRANSCRIPTS_ROOT / show_key
    return base_dir / f"{status_basename}.json", base_dir / f"{status_basename}.md"


def write_run_status_artifacts(
    *,
    show_key: str,
    payload: dict[str, Any],
    status_basename: str = "mallers_bitpod_status",
) -> tuple[Path, Path]:
    json_path, md_path = status_paths(show_key, status_basename=status_basename)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    is_success = payload.get("run_status") == "ok" and bool(payload.get("included_in_pointer"))
    headline = "SUCCESS" if is_success else "FAILED"
    lines = [f"# {headline}", ""]
    lines.append(f"- show: `{payload.get('show_key', show_key)}`")
    lines.append(f"- run_id: `{payload.get('run_id', '')}`")
    lines.append(f"- run_status: `{payload.get('run_status', '')}`")
    lines.append(f"- latest_episode_title: `{payload.get('latest_episode_title', '')}`")
    lines.append(f"- latest_episode_guid: `{payload.get('latest_episode_guid', '')}`")
    lines.append(f"- latest_episode_published_at_utc: `{payload.get('latest_episode_published_at_utc', '')}`")
    lines.append(f"- included_in_pointer: `{payload.get('included_in_pointer', False)}`")
    lines.append(f"- pointer_path: `{payload.get('pointer_path', '')}`")
    lines.append(f"- pointer_updated_at_utc: `{payload.get('pointer_updated_at_utc', '')}`")
    lines.append(f"- plain_artifact_path: `{payload.get('plain_artifact_path', '')}`")
    lines.append(f"- segments_artifact_path: `{payload.get('segments_artifact_path', '')}`")

    failure_stage = payload.get("failure_stage")
    failure_reason = payload.get("failure_reason")
    if failure_stage or failure_reason:
        lines.extend(["", "## Failure Details"])
        lines.append(f"- failure_stage: `{failure_stage}`")
        lines.append(f"- failure_reason: `{failure_reason}`")
        lines.append(f"- suggested_next_action: `{payload.get('suggested_next_action', '')}`")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
