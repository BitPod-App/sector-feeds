from __future__ import annotations

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
