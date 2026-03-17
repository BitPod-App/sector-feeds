from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yt_dlp

LOGGER = logging.getLogger(__name__)
TIMECODE_RE = re.compile(r"^\d\d:\d\d:\d\d[.,]\d+\s+-->\s+\d\d:\d\d:\d\d[.,]\d+.*$")
TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"\s+")
ALIGN_TOKEN_RE = re.compile(r"\b(align|position|size|line):\S+\b")


@dataclass
class CaptionCue:
    start: float
    end: float
    text: str


@dataclass
class CaptionExtraction:
    text: str
    cues: list[CaptionCue]
    quality: dict[str, float | int | bool]
    provenance: str


def download_youtube_audio(source_url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(id)s.%(ext)s")
    progress_state: dict[str, int] = {"last_percent": -1}
    progress_lock = threading.Lock()

    def _progress_hook(payload: dict[str, Any]) -> None:
        if payload.get("status") != "downloading":
            return
        total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
        downloaded = payload.get("downloaded_bytes")
        if not isinstance(total, (int, float)) or not isinstance(downloaded, (int, float)) or total <= 0:
            return

        percent = int((downloaded / total) * 100)
        # Throttle log spam: only emit every 10% plus completion.
        bucket = min(100, (percent // 10) * 10)
        with progress_lock:
            if bucket <= progress_state["last_percent"]:
                return
            progress_state["last_percent"] = bucket
        LOGGER.info("YouTube download progress: %s%%", bucket)

    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [_progress_hook],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source_url, download=True)
        downloaded = ydl.prepare_filename(info)

    media_path = Path(downloaded)
    if not media_path.exists():
        raise FileNotFoundError(f"Downloaded file not found: {media_path}")
    LOGGER.info("Downloaded YouTube audio to %s", media_path)
    return media_path


def _parse_ts(ts: str) -> float:
    hh, mm, ss = ts.replace(",", ".").split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def _clean_cue_text(text: str) -> str:
    cleaned = ALIGN_TOKEN_RE.sub("", text)
    cleaned = TAG_RE.sub("", cleaned)
    cleaned = MULTISPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _parse_vtt_cues(vtt_path: Path) -> list[CaptionCue]:
    lines = vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    cues: list[CaptionCue] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("WEBVTT") or line.startswith("NOTE"):
            i += 1
            continue
        if "-->" not in line and i + 1 < len(lines) and "-->" in lines[i + 1]:
            i += 1
            line = lines[i].strip()
        if "-->" not in line:
            i += 1
            continue
        if not TIMECODE_RE.match(line):
            i += 1
            continue
        start_raw, end_raw = [part.strip() for part in line.split("-->", 1)]
        end_raw = end_raw.split(" ", 1)[0].strip()
        i += 1
        buf: list[str] = []
        while i < len(lines) and lines[i].strip():
            buf.append(lines[i].strip())
            i += 1
        text = _clean_cue_text(" ".join(buf))
        if text:
            cues.append(CaptionCue(start=_parse_ts(start_raw), end=_parse_ts(end_raw), text=text))
        i += 1
    return cues


def _stitch_cues_dedup(cues: list[CaptionCue], max_overlap_words: int = 30) -> str:
    out_words: list[str] = []
    for cue in cues:
        words = cue.text.split()
        if not words:
            continue
        tail = out_words[-max_overlap_words:] if out_words else []
        overlap = 0
        max_k = min(len(words), len(tail))
        for k in range(max_k, 0, -1):
            if tail[-k:] == words[:k]:
                overlap = k
                break
        out_words.extend(words[overlap:])
    return " ".join(out_words).strip()


def _repetition_ratio_5gram(text: str) -> float:
    words = text.split()
    if len(words) < 10:
        return 1.0 if words else 0.0
    grams = [" ".join(words[i : i + 5]) for i in range(len(words) - 4)]
    if not grams:
        return 0.0
    counts: dict[str, int] = {}
    for gram in grams:
        counts[gram] = counts.get(gram, 0) + 1
    repeated = sum(value for value in counts.values() if value > 1)
    return repeated / len(grams)


def _lexical_diversity(text: str) -> float:
    words = [word.lower() for word in text.split() if word.strip()]
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _captions_are_bad(stitched_text: str, cue_count: int, min_words: int) -> tuple[bool, dict[str, float | int | bool]]:
    words = len(stitched_text.split())
    repetition = _repetition_ratio_5gram(stitched_text)
    lexical_diversity = _lexical_diversity(stitched_text)
    cue_density = cue_count / max(1, words)
    bad = (
        words < min_words
        or repetition > 0.10
        or (lexical_diversity < 0.18 and words > 800)
        or (cue_count > 2000 and words < 3000)
        or cue_density > 0.9
    )
    return bad, {
        "bad": bad,
        "word_count": words,
        "cue_count": cue_count,
        "repetition_ratio_5gram": round(repetition, 6),
        "lexical_diversity": round(lexical_diversity, 6),
        "cue_density": round(cue_density, 6),
    }


def _extract_youtube_caption_payload_once(
    source_url: str,
    output_dir: Path,
    *,
    min_words: int,
    automatic_only: bool,
) -> CaptionExtraction | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(output_dir / "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": not automatic_only,
        "writeautomaticsub": automatic_only,
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
        parsed = urlparse(source_url)
        video_id = (parsed.query or "").split("v=")[-1].split("&")[0]
    if not video_id:
        return None

    vtt_files = sorted(output_dir.glob(f"{video_id}*.vtt"))
    if not vtt_files:
        return None

    cues = _parse_vtt_cues(vtt_files[0])
    if not cues:
        return None
    stitched_text = _stitch_cues_dedup(cues)
    bad, quality = _captions_are_bad(stitched_text, len(cues), min_words=min_words)
    if bad:
        return None
    provenance = "youtube_auto_captions" if automatic_only else "official_youtube_captions"
    return CaptionExtraction(text=stitched_text, cues=cues, quality=quality, provenance=provenance)


def extract_youtube_caption_payload(source_url: str, output_dir: Path, min_words: int = 120) -> CaptionExtraction | None:
    official = _extract_youtube_caption_payload_once(
        source_url,
        output_dir / "official",
        min_words=min_words,
        automatic_only=False,
    )
    if official is not None:
        return official
    return _extract_youtube_caption_payload_once(
        source_url,
        output_dir / "automatic",
        min_words=min_words,
        automatic_only=True,
    )


def extract_youtube_captions(source_url: str, output_dir: Path, min_words: int = 120) -> str | None:
    payload = extract_youtube_caption_payload(source_url, output_dir, min_words=min_words)
    if not payload:
        return None
    return payload.text


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
        return download_youtube_audio(str(episode.source_url), output_dir)

    media_url = getattr(episode, "media_url", None)
    if media_url:
        return download_direct_media(str(media_url), output_dir, filename_hint=filename_hint)

    raise RuntimeError(f"No downloadable media source for episode: {episode.source_url}")
