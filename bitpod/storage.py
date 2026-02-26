from __future__ import annotations

import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitpod.indexer import now_iso
from bitpod.paths import ROOT, TRANSCRIPTS_ROOT

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
ROBOTS_POLICY = "noindex, nofollow, noarchive"


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


def status_paths(show_key: str, status_basename: str = "latest_bitpod_status") -> tuple[Path, Path]:
    base_dir = TRANSCRIPTS_ROOT / show_key
    return base_dir / f"{status_basename}.json", base_dir / f"{status_basename}.md"


def write_run_status_artifacts(
    *,
    show_key: str,
    payload: dict[str, Any],
    status_basename: str = "latest_bitpod_status",
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


def write_gpt_review_request(
    *,
    show_key: str,
    payload: dict[str, Any],
    status_basename: str = "latest_bitpod_status",
) -> Path:
    review_basename = status_basename.replace("_status", "_gpt_review_request")
    _, md_status = status_paths(show_key, status_basename=status_basename)
    review_path = md_status.with_name(f"{review_basename}.md")
    review_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# GPT Review Request",
        "",
        "Use this file to review the latest ingestion/transcription run and provide actionable QA feedback.",
        "",
        "## Run Summary",
        f"- show_key: `{payload.get('show_key')}`",
        f"- run_id: `{payload.get('run_id')}`",
        f"- run_status: `{payload.get('run_status')}`",
        f"- latest_episode_title: `{payload.get('latest_episode_title')}`",
        f"- latest_episode_guid: `{payload.get('latest_episode_guid')}`",
        f"- latest_episode_published_at_utc: `{payload.get('latest_episode_published_at_utc')}`",
        f"- included_in_pointer: `{payload.get('included_in_pointer')}`",
        "",
        "## Artifacts",
        f"- pointer_path: `{payload.get('pointer_path')}`",
        f"- status_json_path: `{payload.get('status_json_path')}`",
        f"- status_md_path: `{payload.get('status_md_path')}`",
        f"- plain_artifact_path: `{payload.get('plain_artifact_path')}`",
        f"- segments_artifact_path: `{payload.get('segments_artifact_path')}`",
        "",
        "## Failure Context",
        f"- failure_stage: `{payload.get('failure_stage')}`",
        f"- failure_reason: `{payload.get('failure_reason')}`",
        f"- suggested_next_action: `{payload.get('suggested_next_action')}`",
        "",
        "## GPT Instructions",
        "- If run failed: explain root cause, likely fix, and lowest-risk retry path.",
        "- If run succeeded: assess transcript quality (clarity, duplication, structure, speaker usefulness).",
        "- Provide concise patch recommendations to improve reliability and quality.",
        "- Flag whether transcript is usable for downstream macro/bitcoin event processing.",
        "",
        "## Expected GPT Output Format",
        "1. Status assessment (`usable` / `degraded` / `failed`)",
        "2. Quality findings (ordered by severity)",
        "3. Suggested fixes (specific and testable)",
        "4. Retry recommendation (yes/no + command)",
    ]
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review_path


def _permalink_salt() -> str:
    configured = os.environ.get("BITPOD_PUBLIC_ID_SALT", "").strip()
    if configured:
        return configured
    # Root-derived fallback keeps IDs stable without exposing show keys in public URLs.
    return hashlib.sha256(str(ROOT).encode("utf-8", errors="ignore")).hexdigest()


def _public_permalink_id(show_key: str) -> str:
    raw = f"{_permalink_salt()}::{show_key}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]


def _public_permalink_root() -> Path:
    return ROOT / "artifacts" / "public" / "permalinks"


def _private_manifest_path() -> Path:
    return ROOT / "artifacts" / "private" / "public_permalink_manifest.json"


def _write_noindex_guards(public_root: Path) -> None:
    headers_path = public_root / "_headers"
    headers_path.write_text(f"/*\n  X-Robots-Tag: {ROBOTS_POLICY}\n", encoding="utf-8")
    robots_path = public_root / "robots.txt"
    robots_path.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")


def write_public_permalink_artifacts(
    *,
    show_key: str,
    status_payload: dict[str, Any],
) -> dict[str, str]:
    permalink_id = _public_permalink_id(show_key)
    public_root = _public_permalink_root()
    show_root = public_root / permalink_id
    show_root.mkdir(parents=True, exist_ok=True)
    _write_noindex_guards(public_root)

    latest_path = show_root / "latest.md"
    pointer_path = Path(str(status_payload.get("pointer_path") or ""))
    if pointer_path.exists():
        content = pointer_path.read_text(encoding="utf-8")
        prologue = (
            "<!--\n"
            f"robots: {ROBOTS_POLICY}\n"
            f"x-robots-tag: {ROBOTS_POLICY}\n"
            "-->\n\n"
        )
        latest_text = prologue + content.lstrip()
        if not latest_text.endswith("\n"):
            latest_text += "\n"
        latest_path.write_text(latest_text, encoding="utf-8")
    elif not latest_path.exists():
        latest_path.write_text(
            (
                "<!--\n"
                f"robots: {ROBOTS_POLICY}\n"
                f"x-robots-tag: {ROBOTS_POLICY}\n"
                "-->\n\n"
                "# Unavailable\n\nLatest transcript not currently available.\n"
            ),
            encoding="utf-8",
        )

    status_path = show_root / "status.json"
    public_status = {
        "public_id": permalink_id,
        "run_id": status_payload.get("run_id"),
        "run_status": status_payload.get("run_status"),
        "included_in_pointer": bool(status_payload.get("included_in_pointer")),
        "latest_episode_published_at_utc": status_payload.get("latest_episode_published_at_utc"),
        "pointer_updated_at_utc": status_payload.get("pointer_updated_at_utc"),
        "updated_at_utc": now_iso(),
        "robots": ROBOTS_POLICY,
        "latest_path": "latest.md",
    }
    status_path.write_text(json.dumps(public_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = _private_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"version": 1, "generated_at_utc": now_iso(), "shows": {}}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                manifest.update(existing)
                if not isinstance(manifest.get("shows"), dict):
                    manifest["shows"] = {}
        except json.JSONDecodeError:
            pass
    manifest["generated_at_utc"] = now_iso()
    manifest["id_strategy"] = "sha256(salt::show_key)[:16]"
    manifest["salt_env"] = "BITPOD_PUBLIC_ID_SALT"
    manifest["shows"][show_key] = {
        "public_id": permalink_id,
        "public_dir": str(show_root),
        "latest_md_path": str(latest_path),
        "status_json_path": str(status_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "public_permalink_id": permalink_id,
        "public_permalink_latest_path": str(latest_path),
        "public_permalink_status_path": str(status_path),
        "public_permalink_manifest_path": str(manifest_path),
    }
