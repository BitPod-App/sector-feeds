from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests
import yt_dlp

LOGGER = logging.getLogger(__name__)


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


def download_direct_media(media_url: str, output_dir: Path, filename_hint: str = "episode_media") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(media_url.split("?")[0]).suffix or ".bin"
    target = output_dir / f"{filename_hint}{suffix}"

    with requests.get(media_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)

    LOGGER.info("Downloaded direct media to %s", target)
    return target


def acquire_media(episode: Any, output_dir: Path) -> Path:
    if str(getattr(episode, "source_type", "")).startswith("youtube"):
        return download_youtube_audio(str(episode.source_url), output_dir)

    media_url = getattr(episode, "media_url", None)
    if media_url:
        return download_direct_media(str(media_url), output_dir)

    raise RuntimeError(f"No downloadable media source for episode: {episode.source_url}")
