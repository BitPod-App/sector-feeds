from __future__ import annotations

import json
import os
import re
import hashlib
from html import escape as html_escape
from shutil import copyfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from bitpod.indexer import now_iso
from bitpod.indexer import canonical_episode_id
from bitpod.paths import ROOT, TRANSCRIPTS_ROOT

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
ROBOTS_POLICY = "noindex, nofollow, noarchive"
PUBLIC_BUNDLE_FILES = ("status.json", "intake.md", "transcript.md", "discovery.json")
LANDING_LOGO_PATH = ROOT.parent / "bitpod-assets" / "assets" / "brand" / "logo" / "svg" / "bitpod-logo-avatar-square-color.svg"


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
    lines.append(f"- transcript_provenance: `{payload.get('transcript_provenance', 'failed')}`")
    lines.append(f"- transcript_source_type: `{payload.get('transcript_source_type', '')}`")
    lines.append(f"- transcript_source_url: `{payload.get('transcript_source_url', '')}`")
    lines.append(f"- plain_artifact_path: `{payload.get('plain_artifact_path', '')}`")
    lines.append(f"- segments_artifact_path: `{payload.get('segments_artifact_path', '')}`")
    lines.append(f"- gpt_review_artifact_path: `{payload.get('gpt_review_artifact_path', '')}`")

    governance = payload.get("governance")
    if isinstance(governance, dict):
        provenance = governance.get("provenance_tuple") or {}
        spec_lock = governance.get("spec_lock") or {}
        override_guard = governance.get("override_guard") or {}
        lines.extend(["", "## Governance"])
        lines.append(f"- origin_actor: `{provenance.get('origin_actor', '')}`")
        lines.append(f"- authority_state: `{provenance.get('authority_state', '')}`")
        lines.append(f"- expansion_gate: `{spec_lock.get('expansion_gate', 'BLOCKED')}`")
        lines.append(f"- override_guard_required: `{bool(override_guard.get('required'))}`")
        lines.append(f"- override_guard_complete: `{bool(override_guard.get('complete'))}`")
        missing = override_guard.get("missing_fields") or []
        lines.append(f"- override_guard_missing_fields: `{', '.join(missing) if missing else ''}`")

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
        "# GPT QA Handoff",
        "",
        "Use the public permalink bundle as the canonical input surface for this run.",
        "Do not rely on local filesystem paths as the primary evidence surface.",
        "",
        "## Canonical Permalink Bundle",
        f"- status_json_url: `{payload.get('public_permalink_status_url')}`",
        f"- intake_md_url: `{payload.get('public_permalink_intake_url')}`",
        f"- transcript_md_url: `{payload.get('public_permalink_transcript_url')}`",
        f"- discovery_json_url: `{payload.get('public_permalink_discovery_url')}`",
        "",
        "## Run Contract Summary",
        f"- show_key: `{payload.get('show_key')}`",
        f"- run_id: `{payload.get('run_id')}`",
        f"- run_status: `{payload.get('run_status')}`",
        f"- new_episode_detected: `{bool(payload.get('new_episode_detected'))}`",
        f"- included_in_pointer: `{bool(payload.get('included_in_pointer'))}`",
        f"- episode_title: `{payload.get('episode_title') or payload.get('latest_episode_title')}`",
        f"- episode_guid: `{payload.get('episode_guid') or payload.get('latest_episode_guid')}`",
        f"- episode_url: `{payload.get('episode_url') or payload.get('attempted_source_url')}`",
        f"- published_at_utc: `{payload.get('published_at_utc') or payload.get('latest_episode_published_at_utc')}`",
        f"- transcript_provenance: `{payload.get('transcript_provenance', 'failed')}`",
        f"- source_mode: `{payload.get('source_mode')}`",
        f"- transcript_quality_state: `{payload.get('transcript_quality_state')}`",
        f"- transcript_degraded: `{bool(payload.get('transcript_degraded'))}`",
        f"- fallback_used: `{bool(payload.get('fallback_used'))}`",
        f"- fallback_note: `{payload.get('fallback_note')}`",
        f"- failure_stage: `{payload.get('failure_stage')}`",
        f"- failure_reason: `{payload.get('failure_reason')}`",
        "",
        "## Secondary Local Debug Paths",
        f"- status_json_path: `{payload.get('status_json_path')}`",
        f"- status_md_path: `{payload.get('status_md_path')}`",
        f"- pointer_path: `{payload.get('pointer_path')}`",
        f"- plain_artifact_path: `{payload.get('plain_artifact_path')}`",
        f"- segments_artifact_path: `{payload.get('segments_artifact_path')}`",
        f"- gpt_review_artifact_path: `{payload.get('gpt_review_artifact_path')}`",
        "",
        "## Required ChatGPT Tasks",
        "1. Determine whether there is a new episode or not.",
        "2. Assess the intake/transcript state as exactly one of: `usable`, `degraded`, `failed`, `no-new-episode`.",
        "3. Provide immediate QA feedback for this run.",
        "4. Provide intake-system improvement feedback based on the evidence in the permalink bundle.",
        "5. Produce a basic BTC output report whose wording changes honestly based on intake outcome.",
        "",
        "## Truthful Output Rules",
        "- If a successful new episode intake occurred: mention the episode title and transcript provenance, and treat the episode as low-weight context by default unless clearly material.",
        "- If no new episode was detected: explicitly say no new episode was incorporated.",
        "- If a new episode was detected but intake/transcript failed: explicitly say the episode was not incorporated due to intake failure.",
        "- If transcript quality was degraded: explicitly say the episode was incorporated only as low-confidence context.",
        "- Always produce the BTC output report, even if intake failed or no new episode exists.",
        "",
        "## Required ChatGPT Response Structure",
        "### 1. Intake status assessment",
        "Return exactly one of: `usable`, `degraded`, `failed`, `no-new-episode`.",
        "",
        "### 2. Run findings",
        "Ordered by severity, concise and actionable.",
        "",
        "### 3. Immediate suggested fixes",
        "Specific fixes for the current run failure or degradation, if any.",
        "",
        "### 4. Intake-system recommendations",
        "Recommend serious intake and artifact improvements when supported by the evidence, including source preference, matching logic, fallback behavior, caption/transcript quality gates, permalink fields, and artifact clarity.",
        "",
        "### 5. Episode incorporation guidance",
        "Classify the episode as exactly one of: `omitted`, `noise`, `low-confidence context`, `normal context`.",
        "",
        "### 6. Basic BTC output report",
        "Always include:",
        "- intake state note",
        "- whether a new episode was incorporated",
        "- 7-day outlook",
        "- 30-day outlook",
        "- key factors",
        "- confidence/caveats",
    ]
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return review_path


def write_gpt_review_artifact(
    *,
    show_key: str,
    payload: dict[str, Any],
    artifact_tag: str | None = None,
) -> Path:
    artifact_root = ROOT / "artifacts" / "private" / "gpt-qa"
    artifact_root.mkdir(parents=True, exist_ok=True)
    slug = slugify(show_key)
    raw_tag = str(artifact_tag or payload.get("run_id") or now_iso()).strip()
    tag = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_tag).strip("_") or "artifact"
    artifact_path = artifact_root / f"{slug}__{tag}__gpt_review_request.md"

    lines = [
        "# GPT QA Handoff",
        "",
        f"- generated_at_utc: `{now_iso()}`",
        f"- show_key: `{payload.get('show_key')}`",
        f"- run_id: `{payload.get('run_id')}`",
        f"- status_json_url: `{payload.get('public_permalink_status_url')}`",
        f"- intake_md_url: `{payload.get('public_permalink_intake_url')}`",
        f"- transcript_md_url: `{payload.get('public_permalink_transcript_url')}`",
        f"- discovery_json_url: `{payload.get('public_permalink_discovery_url')}`",
        f"- new_episode_detected: `{bool(payload.get('new_episode_detected'))}`",
        f"- included_in_pointer: `{bool(payload.get('included_in_pointer'))}`",
        f"- transcript_provenance: `{payload.get('transcript_provenance', 'failed')}`",
        f"- source_mode: `{payload.get('source_mode')}`",
        f"- transcript_quality_state: `{payload.get('transcript_quality_state')}`",
        f"- transcript_degraded: `{bool(payload.get('transcript_degraded'))}`",
        f"- fallback_used: `{bool(payload.get('fallback_used'))}`",
        f"- fallback_note: `{payload.get('fallback_note')}`",
        f"- failure_stage: `{payload.get('failure_stage')}`",
        f"- failure_reason: `{payload.get('failure_reason')}`",
        f"- transcript_source_type: `{payload.get('transcript_source_type')}`",
        f"- transcript_source_url: `{payload.get('transcript_source_url')}`",
        f"- pointer_path: `{payload.get('pointer_path')}`",
        f"- status_json_path: `{payload.get('status_json_path')}`",
        f"- status_md_path: `{payload.get('status_md_path')}`",
        f"- stable_gpt_review_request_path: `{payload.get('gpt_review_request_path')}`",
        "",
        "## GPT Instructions",
        "- Use the public permalink bundle as the primary evidence surface.",
        "- Return the six required sections from the stable GPT QA handoff contract.",
        "- Always produce a BTC output report, even for failed or no-new-episode runs.",
        "- Keep local file paths as secondary debug context only.",
    ]
    artifact_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return artifact_path


def _transcript_quality_state(status_payload: dict[str, Any]) -> str:
    if not bool(status_payload.get("new_episode_detected")):
        return "no-new-episode"
    if status_payload.get("run_status") != "ok" or not bool(status_payload.get("included_in_pointer")):
        return "failed"
    if bool(status_payload.get("transcript_degraded")):
        return "degraded"
    return "usable"


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


def _public_permalink_base_url() -> str:
    raw = os.environ.get("BITPOD_PUBLIC_PERMALINK_BASE_URL", "https://bitpod-public-permalinks.pages.dev").strip()
    return raw.rstrip("/")


def _public_max_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_MAX_EPISODES", "10").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 10
    return max(parsed, 1)


def _public_min_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_MIN_EPISODES", "5").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 5
    return max(parsed, 1)


def _public_long_transcript_threshold_chars() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_LONG_TRANSCRIPT_THRESHOLD_CHARS", "18000").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 18000
    return max(parsed, 1)


def _public_long_min_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_LONG_MIN_EPISODES", "3").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 3
    return max(parsed, 1)


def _public_long_max_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_LONG_MAX_EPISODES", "5").strip()
    try:
        parsed = int(raw)
    except ValueError:
        return 5
    return max(parsed, 1)


def _public_short_min_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_SHORT_MIN_EPISODES", str(_public_min_episodes())).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return _public_min_episodes()
    return max(parsed, 1)


def _public_short_max_episodes() -> int:
    raw = os.environ.get("BITPOD_PUBLIC_SHORT_MAX_EPISODES", str(_public_max_episodes())).strip()
    try:
        parsed = int(raw)
    except ValueError:
        return _public_max_episodes()
    return max(parsed, 1)


def _public_target_total_minutes() -> float:
    raw = os.environ.get("BITPOD_PUBLIC_TARGET_TOTAL_MINUTES", "180").strip()
    try:
        parsed = float(raw)
    except ValueError:
        return 180.0
    return max(parsed, 1.0)


def _write_noindex_guards(public_root: Path) -> None:
    headers_path = public_root / "_headers"
    headers_path.write_text(
        (
            "/*\n"
            f"  X-Robots-Tag: {ROBOTS_POLICY}\n"
            "  Access-Control-Allow-Origin: *\n"
            "\n"
            "/*.md\n"
            "  Content-Type: text/markdown; charset=utf-8\n"
            "\n"
            "/*.json\n"
            "  Content-Type: application/json; charset=utf-8\n"
        ),
        encoding="utf-8",
    )
    robots_path = public_root / "robots.txt"
    robots_path.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")


def _landing_logo_markup() -> str:
    try:
        if LANDING_LOGO_PATH.exists():
            return LANDING_LOGO_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    return ""


def _bundle_verification_mode(readability: dict[str, Any] | None) -> str:
    if not isinstance(readability, dict) or not readability:
        return "unknown"
    modes = {str((value or {}).get("verified_via") or "unknown") for value in readability.values()}
    if modes == {"public_http"}:
        return "public_http"
    if modes == {"local_fs"}:
        return "local_fs_only"
    if "public_http" in modes and "local_fs" in modes:
        return "mixed"
    return "unknown"


def _artifact_readable_label(entry: dict[str, Any] | None) -> str:
    if not isinstance(entry, dict):
        return "unverified"
    readable = entry.get("readable")
    if readable is True:
        return "readable"
    if readable is False:
        return "unreadable"
    return "unverified"


def _landing_intake_state(public_status: dict[str, Any]) -> str:
    quality_state = str(public_status.get("transcript_quality_state") or "").strip()
    if quality_state:
        return quality_state
    return _transcript_quality_state(public_status)


def _landing_state_content(
    *,
    public_status: dict[str, Any],
    intake_state: str,
    verification_mode: str,
    bundle_complete: bool,
) -> dict[str, Any]:
    run_status = str(public_status.get("run_status") or "unknown")
    included_in_pointer = bool(public_status.get("included_in_pointer"))
    new_episode_detected = bool(public_status.get("new_episode_detected"))
    transcript_provenance = str(public_status.get("transcript_provenance") or "unknown")
    failure_stage = str(public_status.get("failure_stage") or "").strip()
    failure_reason = str(public_status.get("failure_reason") or "").strip()
    fallback_note = str(public_status.get("fallback_note") or "").strip()
    source_mode = str(public_status.get("source_mode") or "unknown")
    transcript_source_type = str(public_status.get("transcript_source_type") or "unknown")

    if intake_state == "usable":
        summary_text = (
            "New episode detected and incorporated with a usable transcript. Treat it as low-weight context by default unless downstream analysis finds clear signal."
        )
        outcome_line = "Episode was incorporated into the stable pointer with a usable transcript."
        findings_items = [
            "New episode detected: true.",
            "Episode incorporated into pointer: true.",
            f"Transcript provenance: {transcript_provenance}.",
            f"Verification mode: {verification_mode}.",
        ]
        recommendations_items = [
            "Keep the episode as low-weight default context, not a forced driver of the BTC output.",
            f"Keep source mode explicit. Current mode: {source_mode}.",
            f"Preserve transcript source visibility. Current type: {transcript_source_type}.",
        ]
        provenance_note = (
            f"Generated from the latest stable run bundle. Source mode: {source_mode}. Transcript source: {transcript_source_type}."
        )
    elif intake_state == "degraded":
        summary_text = (
            "New episode detected and incorporated, but transcript quality is degraded. Treat it only as low-confidence context."
        )
        outcome_line = "Episode was incorporated into the stable pointer with degraded transcript quality."
        findings_items = [
            "New episode detected: true.",
            "Episode incorporated into pointer: true.",
            "Transcript quality state: degraded.",
            f"Transcript provenance: {transcript_provenance}.",
        ]
        if fallback_note:
            findings_items.append(f"Fallback note: {fallback_note}.")
        recommendations_items = [
            "Do not treat this transcript as normal-confidence evidence.",
            "Inspect transcript quality and consider rerunning intake before depending on the episode heavily.",
            f"Keep source mode explicit. Current mode: {source_mode}.",
        ]
        provenance_note = (
            f"Generated from a degraded but incorporated run. Source mode: {source_mode}. Transcript source: {transcript_source_type}."
        )
    elif intake_state == "failed":
        if new_episode_detected:
            summary_text = "New episode detected, but intake failed. The episode was not incorporated into the pointer surface."
            outcome_line = "Episode was omitted from the stable pointer because intake did not complete cleanly."
            findings_items = [
                "New episode detected: true.",
                "Episode incorporated into pointer: false.",
                f"Run status: {run_status}.",
            ]
        else:
            summary_text = "Run failed before a usable new-episode incorporation decision was completed."
            outcome_line = "No episode incorporation occurred because the run failed."
            findings_items = [f"Run status: {run_status}."]
        if failure_stage:
            findings_items.append(f"Failure stage: {failure_stage}.")
        if failure_reason:
            findings_items.append(f"Failure reason: {failure_reason}.")
        findings_items.append(f"Verification mode: {verification_mode}.")
        recommendations_items = [
            "Do not treat the current episode as incorporated context for downstream output.",
            "Fix the failure condition, rerun intake, and verify the public bundle again before relying on this page.",
            f"Keep source mode explicit. Current mode: {source_mode}.",
        ]
        provenance_note = (
            f"Generated from a failed intake run. Source mode: {source_mode}. Transcript source: {transcript_source_type}."
        )
    else:
        summary_text = "No new episode was detected on this run. The stable pointer remains unchanged."
        outcome_line = "No episode incorporation occurred because there was no new episode."
        findings_items = [
            "New episode detected: false.",
            "Episode incorporated into pointer: false.",
            f"Verification mode: {verification_mode}.",
        ]
        recommendations_items = [
            "State explicitly that no new episode was incorporated in downstream output.",
            "Keep the prior stable pointer intact until a real new episode is detected.",
            f"Keep source mode explicit. Current mode: {source_mode}.",
        ]
        provenance_note = (
            f"Generated from a no-new-episode run. Source mode: {source_mode}. Transcript source: {transcript_source_type}."
        )

    if not bundle_complete:
        summary_text = f"{summary_text} Public bundle verification is not complete yet."
        recommendations_items.insert(0, "Do not treat this page as canonical until public readability finishes verifying.")

    detail_line = fallback_note or failure_reason
    if not detail_line:
        if bundle_complete and verification_mode == "public_http":
            detail_line = "Public permalink bundle verified via public reads."
        else:
            detail_line = "Public permalink bundle is still waiting on complete public verification."

    return {
        "summary_text": summary_text,
        "detail_line": detail_line,
        "outcome_line": outcome_line,
        "findings_items": findings_items,
        "recommendations_items": recommendations_items,
        "provenance_note": provenance_note,
    }


def render_public_landing_page(*, public_status: dict[str, Any], landing_path: Path, base_url: str | None = None) -> Path:
    permalink_id = str(public_status.get("public_id") or "").strip()
    resolved_base_url = (base_url or _public_permalink_base_url()).rstrip("/")
    if not permalink_id:
        raise ValueError("public_status missing public_id")
    landing_path.parent.mkdir(parents=True, exist_ok=True)
    landing_path.write_text(
        _landing_page_html(permalink_id=permalink_id, base_url=resolved_base_url, public_status=public_status),
        encoding="utf-8",
    )
    return landing_path


def _landing_page_html(*, permalink_id: str, base_url: str, public_status: dict[str, Any]) -> str:
    landing_url = f"{base_url}/{permalink_id}"
    logo_markup = _landing_logo_markup()
    run_status = str(public_status.get("run_status") or "unknown")
    included_in_pointer = bool(public_status.get("included_in_pointer"))
    new_episode_detected = bool(public_status.get("new_episode_detected"))
    quality_state = _landing_intake_state(public_status)
    transcript_provenance = str(public_status.get("transcript_provenance") or "unknown")
    episode_title = str(public_status.get("episode_title") or "No episode selected")
    published_at = str(public_status.get("published_at_utc") or "unknown")
    run_id = str(public_status.get("run_id") or "unknown")
    source_mode = str(public_status.get("source_mode") or "unknown")
    transcript_source_type = str(public_status.get("transcript_source_type") or "unknown")
    transcript_source_url = str(public_status.get("transcript_source_url") or public_status.get("episode_url") or "")
    bundle_complete = bool(public_status.get("public_bundle_complete"))
    bundle_missing = public_status.get("public_bundle_missing") or []
    readability = public_status.get("public_bundle_readability") or {}
    verification_mode = str(
        public_status.get("public_bundle_verification_mode") or _bundle_verification_mode(readability)
    )
    verified_at = str(public_status.get("public_bundle_verified_at_utc") or "pending")
    readability_rows = []
    for name in PUBLIC_BUNDLE_FILES:
        entry = readability.get(name) or {}
        readable_label = _artifact_readable_label(entry)
        readability_rows.append(
            f'          <li><strong>{html_escape(name)}</strong> '
            f'<span>{html_escape(readable_label)}</span> '
            f'<span class="muted-inline">via {html_escape(str(entry.get("verified_via") or "unknown"))}</span></li>'
        )
    links = [
        ("status.json", f"{landing_url}/status.json"),
        ("intake.md", f"{landing_url}/intake.md"),
        ("transcript.md", f"{landing_url}/transcript.md"),
        ("discovery.json", f"{landing_url}/discovery.json"),
        ("latest.md", f"{landing_url}/latest.md"),
    ]
    state_content = _landing_state_content(
        public_status=public_status,
        intake_state=quality_state,
        verification_mode=verification_mode,
        bundle_complete=bundle_complete,
    )
    summary_text = str(state_content["summary_text"])
    detail_line = str(state_content["detail_line"])
    outcome_line = str(state_content["outcome_line"])
    findings_items = [str(item) for item in state_content["findings_items"]]
    recommendations_items = [str(item) for item in state_content["recommendations_items"]]
    provenance_note = str(state_content["provenance_note"])
    recommendations_items.append("Keep public readability visible on the page, not just in raw JSON.")
    provenance_items = [
        ("Published", published_at),
        ("Run ID", run_id),
        ("Verification", verification_mode),
        ("Verified At", verified_at),
        ("Intake State", quality_state),
    ]
    artifact_links_markup = [
        f'              <a class="artifact-link" href="{html_escape(href)}"><span>{html_escape(label)}</span><span>{html_escape(_artifact_readable_label(readability.get(label)) if label in readability else ("stable-pointer" if label == "latest.md" else "public"))}</span></a>'
        for label, href in links
    ]
    status_json = json.dumps(public_status, indent=2, sort_keys=True)
    status_json_attr = html_escape(json.dumps(public_status, sort_keys=True))
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "  <head>",
            '    <meta charset="utf-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1">',
            '    <meta name="robots" content="noindex,nofollow,noarchive">',
            "    <title>BitPod Permalink Bundle</title>",
            '    <link rel="preconnect" href="https://fonts.googleapis.com">',
            '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
            '    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
            "    <style>",
            "      :root { color-scheme: light; }",
            "      * { box-sizing: border-box; }",
            "      body { margin: 0; color: #f4efe8; background: radial-gradient(circle at top left, rgba(255,106,26,0.18), transparent 24%), radial-gradient(circle at 82% 18%, rgba(90,43,231,0.2), transparent 28%), linear-gradient(180deg, #0c122c 0%, #091024 100%); font-family: Inter, Arial, sans-serif; line-height: 1.5; }",
            "      a { color: inherit; text-decoration: none; }",
            "      main { width: min(100% - 32px, 1240px); margin: 0 auto; padding: 28px 0 72px; }",
            "      h1, h2, h3, p { margin: 0; }",
            "      .topbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 28px; }",
            "      .brand-lockup { display: flex; align-items: center; gap: 16px; }",
            "      .brand-mark { width: 58px; height: 58px; border-radius: 18px; display: grid; place-items: center; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); overflow: hidden; }",
            "      .brand-mark svg { width: 100%; height: 100%; display: block; }",
            "      .brand-copy { display: grid; gap: 4px; }",
            "      .eyebrow { color: #f2912c; font-size: 12px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; }",
            "      .muted { color: #b9bfce; }",
            "      .topbar-actions, .button-row, .chip-row, .meta-row { display: flex; flex-wrap: wrap; gap: 10px; }",
            "      .button, .ghost-button { border-radius: 999px; padding: 12px 18px; font-size: 14px; font-weight: 600; border: 1px solid transparent; }",
            "      .button { color: #1d1430; background: linear-gradient(135deg, #ffb12a, #ff6a1a); box-shadow: 0 10px 28px rgba(242,145,44,0.26); }",
            "      .ghost-button { color: #f4efe8; background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.12); }",
            "      .hero-card, .section-card, .rail-card, .stat-card { background: linear-gradient(180deg, rgba(26,35,85,0.94), rgba(17,24,58,0.94)); border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 14px 40px rgba(0,0,0,0.28); }",
            "      .hero-card { position: relative; overflow: hidden; border-radius: 42px; padding: 34px; margin-bottom: 24px; }",
            "      .hero-card::after { content: ''; position: absolute; inset: auto -120px -140px auto; width: 340px; height: 340px; background: radial-gradient(circle, rgba(217,69,193,0.38), transparent 60%); pointer-events: none; }",
            "      .hero-grid { display: grid; grid-template-columns: minmax(0, 1.25fr) 320px; gap: 26px; align-items: stretch; }",
            "      .hero-copy { display: grid; gap: 18px; position: relative; z-index: 1; }",
            "      .hero-copy h1 { font-size: clamp(42px, 6vw, 72px); line-height: 0.96; max-width: 12ch; letter-spacing: -0.05em; }",
            "      .hero-copy p { font-size: 18px; max-width: 58ch; }",
            "      .hero-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }",
            "      .stat-card { border-radius: 18px; padding: 18px; }",
            "      .stat-card span { display: block; color: #b9bfce; font-size: 12px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 8px; }",
            "      .stat-card strong { font-size: 24px; letter-spacing: -0.03em; }",
            "      .chip { display: inline-flex; align-items: center; gap: 8px; padding: 9px 12px; border-radius: 999px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); font-size: 13px; color: #b9bfce; }",
            "      .chip strong { color: #f4efe8; }",
            "      .chip.ok strong { color: #7ed1a8; }",
            "      .chip.hot strong { color: #f2912c; }",
            "      .chip.warn strong { color: #ffce7a; }",
            "      .summary-panel { border-radius: 30px; padding: 20px; background: linear-gradient(180deg, rgba(12,18,44,0.34), rgba(12,18,44,0.12)), linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03)); border: 1px solid rgba(255,255,255,0.1); display: grid; gap: 14px; min-height: 100%; }",
            "      .summary-panel .panel-tag { display: inline-flex; align-items: center; padding: 7px 12px; border-radius: 999px; width: fit-content; background: rgba(17,24,58,0.82); border: 1px solid rgba(255,255,255,0.12); font-size: 13px; }",
            "      .summary-panel .logo-box { width: 112px; height: 112px; border-radius: 28px; padding: 16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); display: grid; place-items: center; }",
            "      .summary-panel .logo-box svg { width: 100%; height: 100%; display: block; }",
            "      .summary-panel strong { font-size: 24px; letter-spacing: -0.03em; }",
            "      .content-grid { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 22px; }",
            "      .stack { display: grid; gap: 18px; }",
            "      .section-card, .rail-card { border-radius: 32px; padding: 24px; }",
            "      .section-card h3, .rail-card h3 { margin: 10px 0; font-size: 24px; letter-spacing: -0.03em; }",
            "      .section-card ul, .rail-card ul { margin: 14px 0 0; padding-left: 18px; color: #b9bfce; }",
            "      .section-card li + li, .rail-card li + li { margin-top: 8px; }",
            "      .artifact-list, .meta-list { display: grid; gap: 10px; margin-top: 16px; }",
            "      .artifact-link, .meta-line { display: flex; justify-content: space-between; align-items: center; gap: 14px; padding: 12px 14px; border-radius: 16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); }",
            "      .artifact-link span:last-child, .meta-line span:last-child { color: #b9bfce; font-size: 13px; }",
            "      code, pre { background: rgba(255,255,255,0.07); border-radius: 10px; }",
            "      pre { padding: 1rem; overflow-x: auto; color: #f4efe8; }",
            "      .contract { max-height: 420px; overflow: auto; }",
            "      .footer { margin-top: 42px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; gap: 20px; color: #b9bfce; font-size: 13px; }",
            "      @media (max-width: 1100px) { .hero-grid, .content-grid { grid-template-columns: 1fr; } }",
            "      @media (max-width: 760px) { main { width: min(100% - 20px, 1240px); padding-top: 20px; } .topbar { flex-direction: column; align-items: flex-start; } .hero-card, .section-card, .rail-card { border-radius: 26px; padding: 20px; } .hero-copy h1 { font-size: 42px; } .hero-metrics { grid-template-columns: 1fr; } .footer { flex-direction: column; } }",
            "    </style>",
            "  </head>",
            "  <body>",
            "    <main>",
            '      <header class="topbar">',
            '        <div class="brand-lockup">',
            f'          <div class="brand-mark">{logo_markup}</div>' if logo_markup else '          <div class="brand-mark"></div>',
            '          <div class="brand-copy">',
            '            <span class="eyebrow">BitPod App / permalink report</span>',
            '            <strong>Primary canonical surface</strong>',
            '            <span class="muted">One shell, one summary card, one evidence rail</span>',
            "          </div>",
            "        </div>",
            '        <div class="topbar-actions">',
            f'          <a class="ghost-button" href="{html_escape(landing_url)}/status.json">Open status</a>',
            f'          <a class="button" href="{html_escape(landing_url)}/transcript.md">Open transcript</a>',
            "        </div>",
            "      </header>",
            '      <section class="hero-card">',
            '        <div class="hero-grid">',
            '          <div class="hero-copy">',
            '            <span class="eyebrow">Permalink bundle</span>',
            f'            <h1>{html_escape(episode_title)}</h1>',
            f'            <p class="muted">{html_escape(summary_text)}</p>',
            '            <div class="chip-row">',
            f'              <span class="chip {"ok" if bundle_complete else "warn"}"><strong>{"Verified" if bundle_complete else "Pending"}</strong> bundle health</span>',
            f'              <span class="chip hot"><strong>{html_escape(transcript_provenance)}</strong> transcript provenance</span>',
            f'              <span class="chip"><strong>Run ID</strong> {html_escape(run_id)}</span>',
            f'              <span class="chip {"warn" if new_episode_detected and included_in_pointer else ""}"><strong>{"Included" if included_in_pointer else "Not included"}</strong> pointer state</span>',
            "            </div>",
            '            <div class="hero-metrics">',
            f'              <div class="stat-card"><span>Run status</span><strong>{html_escape(run_status.upper())}</strong></div>',
            f'              <div class="stat-card"><span>Transcript state</span><strong>{html_escape(quality_state)}</strong></div>',
            f'              <div class="stat-card"><span>Verified</span><strong>{html_escape(verified_at)}</strong></div>',
            "            </div>",
            "          </div>",
            '          <aside class="summary-panel">',
            '            <span class="panel-tag">Runtime summary</span>',
            f'            <div class="logo-box">{logo_markup}</div>' if logo_markup else '            <div class="logo-box"></div>',
            f'            <strong>{html_escape("Public bundle complete" if bundle_complete else "Verification pending")}</strong>',
            f'            <p class="muted">{html_escape(detail_line)}</p>',
            "          </aside>",
            "        </div>",
            "      </section>",
            '      <section class="content-grid">',
            '        <div class="stack">',
            '          <article class="section-card">',
            '            <span class="eyebrow">Executive summary</span>',
            '            <h3>What happened</h3>',
            f'            <p class="muted">{html_escape(summary_text)}</p>',
            f'            <p class="muted" style="margin-top: 12px;">{html_escape(outcome_line)}</p>',
            "          </article>",
            '          <article class="section-card">',
            '            <span class="eyebrow">Run findings</span>',
            '            <h3>Current intake surface</h3>',
            "            <ul>",
            *[f'              <li>{html_escape(item)}</li>' for item in findings_items],
            "            </ul>",
            "          </article>",
            '          <article class="section-card">',
            '            <span class="eyebrow">Recommendations</span>',
            '            <h3>Current system posture</h3>',
            "            <ul>",
            *[f'              <li>{html_escape(item)}</li>' for item in recommendations_items],
            "            </ul>",
            "          </article>",
            '          <article class="section-card">',
            '            <span class="eyebrow">Public readability</span>',
            '            <h3>Nested artifact state</h3>',
            f'            <p class="muted">{"Verified via public reads." if verification_mode == "public_http" and bundle_complete else "Public verification is incomplete or mixed."} Missing after verification: {html_escape(", ".join(bundle_missing) if bundle_missing else "none")}.</p>',
            "            <ul>",
            *readability_rows,
            "            </ul>",
            "          </article>",
            '          <article class="section-card">',
            '            <span class="eyebrow">Run contract</span>',
            '            <h3>Machine-readable payload</h3>',
            f'            <script id="bitpod-run-contract" type="application/json" data-public-id="{html_escape(permalink_id)}">{status_json_attr}</script>',
            f'            <pre class="contract">{html_escape(status_json)}</pre>',
            "          </article>",
            "        </div>",
            '        <aside class="stack">',
            '          <article class="rail-card">',
            '            <span class="eyebrow">Artifact rail</span>',
            '            <h3>Canonical evidence</h3>',
            '            <div class="artifact-list">',
            *artifact_links_markup,
            "            </div>",
            "          </article>",
            '          <article class="rail-card">',
            '            <span class="eyebrow">Metadata</span>',
            '            <h3>Run surface</h3>',
            '            <div class="meta-list">',
            *[
                f'              <div class="meta-line"><span>{html_escape(label)}</span><span>{html_escape(value)}</span></div>'
                for label, value in provenance_items
            ],
            f'              <div class="meta-line"><span>Bundle health</span><span>{"complete" if bundle_complete else "not fully verified"}</span></div>',
            "            </div>",
            "          </article>",
            '          <article class="rail-card">',
            '            <span class="eyebrow">Provenance</span>',
            '            <h3>Minimal footer context</h3>',
            f'            <p class="muted">{html_escape(provenance_note)}</p>',
            f'            <p class="muted" style="margin-top: 12px;">{"Source URL available." if transcript_source_url else "No source URL published."}</p>',
            "          </article>",
            "        </aside>",
            "      </section>",
            '      <footer class="footer"><span>BitPod App / permalink bundle</span><span>Generated surface • public verification aware • evidence-first layout</span></footer>',
            "    </main>",
            "  </body>",
            "</html>",
            "",
        ]
    )


def default_public_bundle_health(*, show_root: Path, base_url: str, permalink_id: str) -> dict[str, Any]:
    readability: dict[str, Any] = {}
    missing: list[str] = []
    for name in PUBLIC_BUNDLE_FILES:
        target = show_root / name
        local_exists = target.exists()
        if not local_exists:
            missing.append(name)
        readability[name] = {
            "url": f"{base_url}/{permalink_id}/{name}",
            "http_status": None,
            "content_type": None,
            "readable": None,
            "local_exists": local_exists,
            "verified_via": "local_fs",
        }
    return {
        "public_bundle_complete": False,
        "public_bundle_readability": readability,
        "public_bundle_missing": missing,
        "public_bundle_verification_mode": "local_fs_only",
        "public_bundle_verified_at_utc": None,
    }


def _parse_iso_or_min(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _show_episode_records(show_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index_path = ROOT / "index" / "processed.json"
    if not index_path.exists():
        return [], []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], []

    processed: list[dict[str, Any]] = []
    unprocessed: list[dict[str, Any]] = []
    prefix = f"{show_key}::"
    for key, payload in (data.get("episodes") or {}).items():
        if not str(key).startswith(prefix):
            continue
        parts = str(key).split("::", 1)
        guid = parts[1] if len(parts) == 2 else str(key)
        sector_feed_id = str(payload.get("sector_feed_id") or show_key)
        feed_episode_id = str(payload.get("feed_episode_id") or payload.get("source_episode_id") or guid)
        canonical_id = payload.get("canonical_episode_id") or canonical_episode_id(sector_feed_id, feed_episode_id)
        status = str(payload.get("status") or "")
        published_at = payload.get("published_at")
        if status == "ok":
            transcript_path = Path(str(payload.get("transcript_path") or ""))
            if transcript_path.exists():
                duration_minutes_est = _estimate_episode_minutes(payload, transcript_path)
                transcript_chars_est = _estimate_transcript_chars(transcript_path)
                processed.append(
                    {
                        "guid": guid,
                        "feed_episode_id": feed_episode_id,
                        "sector_feed_id": sector_feed_id,
                        "canonical_episode_id": canonical_id,
                        "status": "processed",
                        "published_at_utc": published_at,
                        "source_url": payload.get("source_url"),
                        "transcript_path": str(transcript_path),
                        "duration_minutes_est": duration_minutes_est,
                        "transcript_chars_est": transcript_chars_est,
                    }
                )
        else:
            unprocessed.append(
                {
                    "guid": guid,
                    "feed_episode_id": feed_episode_id,
                    "sector_feed_id": sector_feed_id,
                    "canonical_episode_id": canonical_id,
                    "status": status or "unknown",
                    "published_at_utc": published_at,
                    "source_url": payload.get("source_url"),
                    "failure_stage": payload.get("stage"),
                    "failure_reason": payload.get("reason"),
                    "updated_at_utc": payload.get("updated_at"),
                }
            )

    processed.sort(key=lambda item: _parse_iso_or_min(item.get("published_at_utc")))
    unprocessed.sort(key=lambda item: _parse_iso_or_min(item.get("published_at_utc")))
    return processed, unprocessed


def _estimate_episode_minutes(payload: dict[str, Any], transcript_path: Path) -> float:
    segments_path = Path(str(payload.get("transcript_segments_path") or ""))
    if segments_path.is_file():
        max_end = 0.0
        for line in segments_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                end = float(row.get("end") or 0.0)
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
            if end > max_end:
                max_end = end
        if max_end > 0:
            return round(max_end / 60.0, 2)

    if not transcript_path.is_file():
        return 1.0
    text = transcript_path.read_text(encoding="utf-8", errors="ignore")
    words = len(text.split())
    if words <= 0:
        return 1.0
    # Conservative spoken-word estimate.
    return round(max(words / 150.0, 1.0), 2)


def _estimate_transcript_chars(transcript_path: Path) -> int:
    if not transcript_path.is_file():
        return 0
    text = transcript_path.read_text(encoding="utf-8", errors="ignore")
    return len(text.strip())


def _youtube_url_forms(source_url: str | None) -> tuple[str | None, str | None]:
    if not source_url:
        return None, None
    raw = str(source_url).strip()
    if not raw:
        return None, None
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    if "youtu" not in host:
        return raw, raw
    query = parse_qs(parsed.query)
    video_id = None
    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/") or None
    else:
        vals = query.get("v", [])
        if vals:
            video_id = str(vals[0]).strip() or None
    list_vals = query.get("list", [])
    playlist_id = str(list_vals[0]).strip() if list_vals else None
    canonical = f"https://www.youtube.com/watch?v={video_id}" if video_id else raw
    if video_id and playlist_id:
        playlist_qs = urlencode({"v": video_id, "list": playlist_id})
        return canonical, f"https://www.youtube.com/watch?{playlist_qs}"
    return canonical, canonical


def _strip_segments_section(markdown_text: str) -> str:
    marker = "\n## Segments\n"
    if marker in markdown_text:
        return markdown_text.split(marker, 1)[0].rstrip() + "\n"
    return markdown_text


def _select_processed_window(processed: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not processed:
        return [], {
            "min_episodes": _public_min_episodes(),
            "max_episodes": _public_max_episodes(),
            "window_profile": "short_transcript_profile",
            "long_transcript_threshold_chars": _public_long_transcript_threshold_chars(),
            "target_total_minutes": _public_target_total_minutes(),
            "selected_count": 0,
            "selected_total_minutes_est": 0.0,
            "selected_avg_chars_est": 0,
        }

    max_probe = min(len(processed), _public_short_max_episodes())
    newest_probe = processed[-max_probe:] if max_probe > 0 else processed
    char_counts = [int(item.get("transcript_chars_est") or 0) for item in newest_probe]
    avg_chars = int(sum(char_counts) / len(char_counts)) if char_counts else 0
    long_threshold = _public_long_transcript_threshold_chars()
    if avg_chars >= long_threshold:
        min_episodes = _public_long_min_episodes()
        max_episodes = _public_long_max_episodes()
        window_profile = "long_transcript_profile"
    else:
        min_episodes = _public_short_min_episodes()
        max_episodes = _public_short_max_episodes()
        window_profile = "short_transcript_profile"
    if min_episodes > max_episodes:
        min_episodes = max_episodes
    target_minutes = _public_target_total_minutes()

    chosen_newest_first: list[dict[str, Any]] = []
    total_minutes = 0.0
    for item in reversed(processed):
        if len(chosen_newest_first) >= max_episodes:
            break
        chosen_newest_first.append(item)
        total_minutes += float(item.get("duration_minutes_est") or 0.0)
        if len(chosen_newest_first) >= min_episodes and total_minutes >= target_minutes:
            break

    selected = list(reversed(chosen_newest_first))
    meta = {
        "min_episodes": min_episodes,
        "max_episodes": max_episodes,
        "window_profile": window_profile,
        "long_transcript_threshold_chars": long_threshold,
        "target_total_minutes": target_minutes,
        "selected_count": len(selected),
        "selected_total_minutes_est": round(total_minutes, 2),
        "selected_avg_chars_est": avg_chars,
    }
    return selected, meta


def _status_sector_tags(status_payload: dict[str, Any]) -> list[str]:
    raw = status_payload.get("sector_tags")
    if isinstance(raw, list):
        tags = [str(v).strip() for v in raw if str(v).strip()]
    elif isinstance(raw, str) and raw.strip():
        tags = [raw.strip()]
    else:
        tags = []
    # Preserve order, dedupe case-insensitively.
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out


def _status_simple_tags(status_payload: dict[str, Any], key_name: str) -> list[str]:
    raw = status_payload.get(key_name)
    if isinstance(raw, list):
        tags = [str(v).strip() for v in raw if str(v).strip()]
    elif isinstance(raw, str) and raw.strip():
        tags = [raw.strip()]
    else:
        tags = []
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(tag)
    return out


def write_public_permalink_artifacts(
    *,
    show_key: str,
    status_payload: dict[str, Any],
) -> dict[str, str]:
    permalink_id = _public_permalink_id(show_key)
    base_url = _public_permalink_base_url()
    public_root = _public_permalink_root()
    show_root = public_root / permalink_id
    show_root.mkdir(parents=True, exist_ok=True)
    episodes_root = show_root / "episodes"
    episodes_root.mkdir(parents=True, exist_ok=True)
    for old in episodes_root.glob("*.md"):
        old.unlink(missing_ok=True)
    _write_noindex_guards(public_root)

    latest_path = show_root / "latest.md"
    transcript_path = show_root / "transcript.md"
    intake_path = show_root / "intake.md"
    discovery_path = show_root / "discovery.json"
    landing_path = show_root / "index.html"
    processed, unprocessed = _show_episode_records(show_key)
    selected_processed, window_meta = _select_processed_window(processed)
    published_rows: list[dict[str, Any]] = []
    for item in selected_processed:
        src = Path(item["transcript_path"])
        dst = episodes_root / src.name
        copyfile(src, dst)
        row = dict(item)
        row["file"] = f"episodes/{dst.name}"
        canonical_video_url, playlist_context_url = _youtube_url_forms(row.get("source_url"))
        row["canonical_video_url"] = canonical_video_url
        row["playlist_context_url"] = playlist_context_url
        row["playlist_membership_status"] = "unknown"
        row["membership_last_seen_at_utc"] = None
        row["membership_miss_count"] = 0
        published_rows.append(row)

    prologue = (
        "<!--\n"
        f"robots: {ROBOTS_POLICY}\n"
        f"x-robots-tag: {ROBOTS_POLICY}\n"
        "-->\n\n"
    )
    if published_rows:
        lines = [prologue.rstrip(), "", "# Transcript Index", ""]
        lines.append(f"- processed_total_count: `{len(processed)}`")
        lines.append(f"- processed_published_count: `{len(published_rows)}`")
        lines.append(f"- processing_order: `oldest_to_newest`")
        lines.append(f"- window_profile: `{window_meta['window_profile']}`")
        lines.append(f"- min_episodes_window: `{window_meta['min_episodes']}`")
        lines.append(f"- max_episodes_window: `{window_meta['max_episodes']}`")
        lines.append(f"- long_transcript_threshold_chars: `{window_meta['long_transcript_threshold_chars']}`")
        lines.append(f"- selected_avg_chars_est: `{window_meta['selected_avg_chars_est']}`")
        lines.append(f"- target_total_minutes: `{window_meta['target_total_minutes']}`")
        lines.append(f"- selected_total_minutes_est: `{window_meta['selected_total_minutes_est']}`")
        lines.append(f"- unprocessed_count: `{len(unprocessed)}`")
        lines.append("")
        lines.append("## Processed Episodes (oldest to newest)")
        for row in published_rows:
            lines.append(
                f"- {row.get('published_at_utc') or 'unknown'} | "
                f"[{row['file']}]({row['file']}) | guid=`{row['guid']}`"
            )
        if unprocessed:
            lines.extend(["", "## Unprocessed Episodes"])
            for row in unprocessed:
                lines.append(
                    f"- {row.get('published_at_utc') or 'unknown'} | guid=`{row['guid']}` | "
                    f"status=`{row.get('status')}` | stage=`{row.get('failure_stage')}`"
                )
        latest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Stable single-file transcript permalink for GPT consumers.
        newest = published_rows[-1]
        src = episodes_root / Path(str(newest["file"])).name
        if src.exists():
            raw = src.read_text(encoding="utf-8", errors="ignore")
            cleaned = _strip_segments_section(raw)
            transcript_path.write_text(cleaned, encoding="utf-8")
    elif not latest_path.exists():
        latest_path.write_text(
            prologue + "# Unavailable\n\nNo processed transcripts currently available.\n",
            encoding="utf-8",
        )
        if not transcript_path.exists():
            transcript_path.write_text(
                prologue + "# Unavailable\n\nNo processed transcript currently available.\n",
                encoding="utf-8",
            )

    status_path = show_root / "status.json"
    sector_tags = _status_sector_tags(status_payload)
    format_tags = _status_simple_tags(status_payload, "format_tags")
    source_platform_tags = _status_simple_tags(status_payload, "source_platform_tags")
    show_root_rel = str(show_root.relative_to(ROOT))
    published_files = [str(row["file"]) for row in published_rows]
    published_guid_list = [str(row["guid"]) for row in published_rows]
    processed_episode_ids = [str(row.get("feed_episode_id") or row.get("guid")) for row in published_rows]
    processed_canonical_ids = [str(row.get("canonical_episode_id") or "") for row in published_rows if row.get("canonical_episode_id")]
    unprocessed_episode_ids = [str(row.get("feed_episode_id") or row.get("guid")) for row in unprocessed]
    episode_title = status_payload.get("episode_title") or status_payload.get("latest_episode_title")
    episode_guid = status_payload.get("episode_guid") or status_payload.get("latest_episode_guid")
    episode_url = status_payload.get("episode_url") or status_payload.get("attempted_source_url")
    published_at_utc = status_payload.get("published_at_utc") or status_payload.get("latest_episode_published_at_utc")
    transcript_quality_state = str(
        status_payload.get("transcript_quality_state") or _transcript_quality_state(status_payload)
    )
    transcript_degraded = bool(status_payload.get("transcript_degraded") or transcript_quality_state == "degraded")
    fallback_used = bool(status_payload.get("fallback_used"))
    fallback_note = status_payload.get("fallback_note")
    transcript_quality_metrics = {
        "word_count": status_payload.get("quality_word_count"),
        "repetition_ratio_5gram": status_payload.get("quality_repetition_ratio_5gram"),
        "lexical_diversity": status_payload.get("quality_lexical_diversity"),
    }
    transcript_quality_metrics = {k: v for k, v in transcript_quality_metrics.items() if v is not None}
    source_mode = status_payload.get("source_mode")
    if not source_mode and published_rows:
        source_mode = published_rows[-1].get("source_mode")
    bundle_health = default_public_bundle_health(show_root=show_root, base_url=base_url, permalink_id=permalink_id)
    intake_lines = [
        prologue.rstrip(),
        "",
        "# Transcript Intake",
        "",
        f"- public_id: `{permalink_id}`",
        f"- show_key: `{show_key}`",
        f"- run_id: `{status_payload.get('run_id')}`",
        f"- run_status: `{status_payload.get('run_status')}`",
        f"- new_episode_detected: `{bool(status_payload.get('new_episode_detected'))}`",
        f"- intake_status_hint: `{transcript_quality_state}`",
        f"- series_is_feed_unit: `{bool(status_payload.get('series_is_feed_unit', True))}`",
        f"- feed_unit_type: `{status_payload.get('feed_unit_type') or 'series_or_playlist_or_feed'}`",
        f"- included_in_pointer: `{bool(status_payload.get('included_in_pointer'))}`",
        f"- episode_title: `{episode_title}`",
        f"- episode_guid: `{episode_guid}`",
        f"- episode_url: `{episode_url}`",
        f"- published_at_utc: `{published_at_utc}`",
        f"- source_mode: `{source_mode}`",
        f"- transcript_provenance: `{status_payload.get('transcript_provenance', 'failed')}`",
        f"- transcript_source_type: `{status_payload.get('transcript_source_type')}`",
        f"- transcript_source_url: `{status_payload.get('transcript_source_url')}`",
        f"- transcript_quality_state: `{transcript_quality_state}`",
        f"- transcript_degraded: `{transcript_degraded}`",
        f"- fallback_used: `{fallback_used}`",
        f"- fallback_note: `{fallback_note}`",
        f"- failure_stage: `{status_payload.get('failure_stage')}`",
        f"- failure_reason: `{status_payload.get('failure_reason')}`",
        f"- processed_published_count: `{len(published_rows)}`",
        f"- unprocessed_count: `{len(unprocessed)}`",
        "",
        "## Run Summary",
        f"- selected_episode: `{episode_title or 'none'}`",
        f"- selected_episode_new: `{bool(status_payload.get('new_episode_detected'))}`",
        f"- selected_source_path: `{source_mode or 'unknown'}` via `{status_payload.get('transcript_source_type') or status_payload.get('attempted_source_type') or 'unknown'}`",
        f"- transcript_incorporated: `{bool(status_payload.get('included_in_pointer'))}`",
        f"- degradation_or_fallback: `{fallback_note or status_payload.get('failure_reason') or ('none' if not transcript_degraded else transcript_quality_state)}`",
        "",
        "## Stable Discovery Entrypoints",
        "- Human intake: [intake.md](intake.md)",
        "- Human latest transcript: [transcript.md](transcript.md)",
        "- Human transcript index: [latest.md](latest.md)",
        "- Machine status: [status.json](status.json)",
        "- Machine discovery: [discovery.json](discovery.json)",
        "",
        "## Processed Episode Files",
    ]
    if published_files:
        for file_path in published_files:
            intake_lines.append(f"- [{file_path}]({file_path})")
    else:
        intake_lines.append("- none")
    intake_path.write_text("\n".join(intake_lines) + "\n", encoding="utf-8")

    discovery_payload = {
        "contract_version": "public_permalink_discovery.v1",
        "public_id": permalink_id,
        "show_key": show_key,
        "sector_feed_id": show_key,
        "updated_at_utc": now_iso(),
        "entrypoints": {
            "landing_html": "index.html",
            "intake_md": "intake.md",
            "transcript_md": "transcript.md",
            "latest_md": "latest.md",
            "status_json": "status.json",
            "episodes_dir": "episodes/",
        },
        "series_is_feed_unit": bool(status_payload.get("series_is_feed_unit", True)),
        "feed_unit_type": status_payload.get("feed_unit_type") or "series_or_playlist_or_feed",
        "format_tags": format_tags,
        "source_platform_tags": source_platform_tags,
        "published_episode_files": published_files,
        "published_episode_guids": published_guid_list,
        "processed_episode_ids": processed_episode_ids,
        "processed_canonical_episode_ids": processed_canonical_ids,
        "unprocessed_episode_ids": unprocessed_episode_ids,
        "processed_published_count": len(published_rows),
        "unprocessed_count": len(unprocessed),
    }
    discovery_path.write_text(json.dumps(discovery_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    public_status = {
        "contract_version": "public_permalink_status.v1",
        "public_id": permalink_id,
        "sector_tags": sector_tags,
        "format_tags": format_tags,
        "source_platform_tags": source_platform_tags,
        "sector_feed_id": show_key,
        "show_key": show_key,
        "series_is_feed_unit": bool(status_payload.get("series_is_feed_unit", True)),
        "feed_unit_type": status_payload.get("feed_unit_type") or "series_or_playlist_or_feed",
        "show_root": show_root_rel,
        "run_id": status_payload.get("run_id"),
        "run_status": status_payload.get("run_status"),
        "new_episode_detected": bool(status_payload.get("new_episode_detected")),
        "included_in_pointer": bool(status_payload.get("included_in_pointer")),
        "episode_title": episode_title,
        "episode_guid": episode_guid,
        "episode_url": episode_url,
        "published_at_utc": published_at_utc,
        "transcript_provenance": status_payload.get("transcript_provenance", "failed"),
        "source_mode": source_mode,
        "transcript_degraded": transcript_degraded,
        "fallback_used": fallback_used,
        "fallback_note": fallback_note,
        "transcript_quality_state": transcript_quality_state,
        "transcript_quality_metrics": transcript_quality_metrics,
        "failure_stage": status_payload.get("failure_stage"),
        "failure_reason": status_payload.get("failure_reason"),
        "transcript_source_type": status_payload.get("transcript_source_type"),
        "transcript_source_url": status_payload.get("transcript_source_url"),
        "public_bundle_complete": bundle_health["public_bundle_complete"],
        "public_bundle_readability": bundle_health["public_bundle_readability"],
        "public_bundle_missing": bundle_health["public_bundle_missing"],
        "public_bundle_verification_mode": bundle_health["public_bundle_verification_mode"],
        "public_bundle_verified_at_utc": bundle_health["public_bundle_verified_at_utc"],
        "latest_episode_published_at_utc": status_payload.get("latest_episode_published_at_utc"),
        "pointer_updated_at_utc": status_payload.get("pointer_updated_at_utc"),
        "updated_at_utc": now_iso(),
        "robots": ROBOTS_POLICY,
        "landing_path": "index.html",
        "intake_path": "intake.md",
        "transcript_path": "transcript.md",
        "latest_path": "latest.md",
        "discovery_path": "discovery.json",
        "episodes_dir": "episodes/",
        "processed_total_count": len(processed),
        "processed_count": len(published_rows),
        "unprocessed_count": len(unprocessed),
        "processed_episode_ids": processed_episode_ids,
        "processed_canonical_episode_ids": processed_canonical_ids,
        "unprocessed_episode_ids": unprocessed_episode_ids,
        "processing_order": "oldest_to_newest",
        "window_profile": window_meta["window_profile"],
        "min_episodes_window": window_meta["min_episodes"],
        "max_episodes_window": window_meta["max_episodes"],
        "long_transcript_threshold_chars": window_meta["long_transcript_threshold_chars"],
        "selected_avg_chars_est": window_meta["selected_avg_chars_est"],
        "target_total_minutes": window_meta["target_total_minutes"],
        "selected_total_minutes_est": window_meta["selected_total_minutes_est"],
        "processor_mode": "batch_oldest_to_newest",
        "processor_queue_count": len(published_rows),
        "processed_episodes": published_rows,
        "unprocessed_episodes": unprocessed,
    }
    status_path.write_text(json.dumps(public_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_public_landing_page(public_status=public_status, landing_path=landing_path, base_url=base_url)

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
        "sector_tags": sector_tags,
        "format_tags": format_tags,
        "source_platform_tags": source_platform_tags,
        "series_is_feed_unit": bool(status_payload.get("series_is_feed_unit", True)),
        "feed_unit_type": status_payload.get("feed_unit_type") or "series_or_playlist_or_feed",
        "public_dir": str(show_root),
        "landing_html_path": str(landing_path),
        "intake_md_path": str(intake_path),
        "transcript_md_path": str(transcript_path),
        "latest_md_path": str(latest_path),
        "status_json_path": str(status_path),
        "discovery_json_path": str(discovery_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "public_permalink_id": permalink_id,
        "public_permalink_intake_path": str(intake_path),
        "public_permalink_transcript_path": str(transcript_path),
        "public_permalink_latest_path": str(latest_path),
        "public_permalink_status_path": str(status_path),
        "public_permalink_discovery_path": str(discovery_path),
        "public_permalink_landing_path": str(landing_path),
        "public_permalink_manifest_path": str(manifest_path),
        "public_permalink_landing_url": f"{base_url}/{permalink_id}",
        "public_permalink_intake_url": f"{base_url}/{permalink_id}/intake.md",
        "public_permalink_transcript_url": f"{base_url}/{permalink_id}/transcript.md",
        "public_permalink_latest_url": f"{base_url}/{permalink_id}/latest.md",
        "public_permalink_status_url": f"{base_url}/{permalink_id}/status.json",
        "public_permalink_discovery_url": f"{base_url}/{permalink_id}/discovery.json",
    }
