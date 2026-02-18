from __future__ import annotations

import logging
import re
from typing import Any

import requests
import yt_dlp

LOGGER = logging.getLogger(__name__)
CHANNEL_ID_PATTERN = re.compile(r'"channelId"\s*:\s*"([^"]+)"')


def discover_youtube_channel_id(youtube_url_or_handle: str) -> str:
    target = youtube_url_or_handle
    if youtube_url_or_handle.startswith("@"):
        target = f"https://www.youtube.com/{youtube_url_or_handle}"

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
            info = ydl.extract_info(target, download=False)
        channel_id = info.get("channel_id") or info.get("channel")
        if channel_id and str(channel_id).startswith("UC"):
            return str(channel_id)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("yt-dlp channel discovery failed for %s: %s", target, exc)

    response = requests.get(target, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    match = CHANNEL_ID_PATTERN.search(response.text)
    if not match:
        raise RuntimeError(f"Could not discover YouTube channel id from {target}")
    return match.group(1)


def youtube_rss_for_channel_id(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def discover_show_feeds(show: dict[str, Any]) -> dict[str, str]:
    feeds = dict(show.get("feeds", {}))
    handle = show.get("youtube_handle")
    channel_url = show.get("youtube_channel_url")
    if handle or channel_url:
        channel_id = discover_youtube_channel_id(channel_url or handle)
        feeds["youtube"] = youtube_rss_for_channel_id(channel_id)
        feeds["youtube_channel_id"] = channel_id
    return feeds
