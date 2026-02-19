from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import requests
import yt_dlp

LOGGER = logging.getLogger(__name__)
TIMECODE_RE = re.compile(r"^\d\d:\d\d:\d\d[.,]\d+\s+-->\s+\d\d:\d\d:\d\d[.,]\d+$")
TAG_RE = re.compile(r"<[^>]+>")


def download_youtube_audio(source_url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source_url, download=True)
        downloaded = ydl.prepare_filename(info)

    media_path = Path(downloaded)
    if not media_path.exists():
        raise FileNotFoundError(f"Downloaded file not found: {media_path}")
    LOGGER.info("Downloaded YouTube audio to %s", media_path)
    return media_path


def _vtt_to_text(vtt_path: Path) -> str:
    lines: list[str] = []
    for raw in vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.isdigit() or TIMECODE_RE.match(line):
            continue
        cleaned = TAG_RE.sub("", line)
        if cleaned:
            lines.append(cleaned)
    text = "\n".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_youtube_captions(source_url: str, output_dir: Path, min_words: int = 120) -> str | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "outtmpl": outtmpl,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(source_url, download=True)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Caption extraction failed for %s: %s", source_url, exc)
        return None

    video_id = str(info.get("id", "")).strip()
    if not video_id:
        return None

    vtt_files = sorted(output_dir.glob(f"{video_id}*.vtt"))
    if not vtt_files:
        return None

    text = _vtt_to_text(vtt_files[0])
    words = text.split()
    if len(words) < min_words:
        return None
    return text


def download_direct_media(media_url: str, output_dir: Path, filename_hint: str = "episode_media") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(media_url.split("?")[0]).suffix or ".bin"
    target = output_dir / f"{filename_hint}{suffix}"

    with requests.get(media_url, stream=True, timeout=90) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if chunk:
                    handle.write(chunk)

    LOGGER.info("Downloaded direct media to %s", target)
    return target


def acquire_media(episode: Any, output_dir: Path, filename_hint: str = "episode_media") -> Path:
    if str(getattr(episode, "source_type", "")).startswith("youtube"):
        return download_youtube_audio(str(getattr(episode, "source_url", "")), output_dir)

    media_url = getattr(episode, "media_url", None)
    if media_url:
        return download_direct_media(str(media_url), output_dir, filename_hint=filename_hint)

    raise RuntimeError(f"No downloadable media source for episode: {getattr(episode, 'source_url', '<unknown>')}")
