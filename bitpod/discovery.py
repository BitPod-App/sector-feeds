from __future__ import annotations

import logging
import re
from typing import Any

import requests
import yt_dlp

LOGGER = logging.getLogger(__name__)
CHANNEL_ID_PATTERN = re.compile(r'"channelId"\s*:\s*"([^"]+)"')
ANCHOR_ID_PATTERN = re.compile(r"anchor\.fm/s/([a-z0-9]+)/?", re.IGNORECASE)
USER_AGENT = {"User-Agent": "Mozilla/5.0"}


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

    response = requests.get(target, headers=USER_AGENT, timeout=30)
    response.raise_for_status()
    match = CHANNEL_ID_PATTERN.search(response.text)
    if not match:
        raise RuntimeError(f"Could not discover YouTube channel id from {target}")
    return match.group(1)


def youtube_rss_for_channel_id(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def _anchor_rss_from_id(anchor_id: str) -> str:
    return f"https://anchor.fm/s/{anchor_id}/podcast/rss"


def _discover_anchor_rss(show: dict[str, Any]) -> str | None:
    anchor_rss = show.get("anchor_rss")
    if isinstance(anchor_rss, str) and anchor_rss.strip():
        return anchor_rss.strip()

    anchor_id = show.get("anchor_show_id")
    if isinstance(anchor_id, str) and anchor_id.strip():
        return _anchor_rss_from_id(anchor_id.strip())

    # Rare "holy grail" path: infer Anchor id from provided URLs or page content.
    candidate_urls: list[str] = []
    for key in ("website_url", "spotify_url", "apple_podcasts_url"):
        value = show.get(key)
        if isinstance(value, str) and value.strip():
            candidate_urls.append(value.strip())

    for candidate in candidate_urls:
        match = ANCHOR_ID_PATTERN.search(candidate)
        if match:
            return _anchor_rss_from_id(match.group(1))

    if not show.get("discover_anchor_holy_grail"):
        return None

    for candidate in candidate_urls[:2]:
        try:
            response = requests.get(candidate, headers=USER_AGENT, timeout=30)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Anchor discovery fetch failed for %s: %s", candidate, exc)
            continue
        match = ANCHOR_ID_PATTERN.search(response.text)
        if match:
            return _anchor_rss_from_id(match.group(1))

    return None


def _ensure_rss_list(feeds: dict[str, Any]) -> list[str]:
    rss = feeds.get("rss")
    if isinstance(rss, str):
        return [rss] if rss else []
    if isinstance(rss, list):
        return [str(x) for x in rss if x]
    return []


def discover_show_feeds(show: dict[str, Any]) -> dict[str, Any]:
    feeds: dict[str, Any] = dict(show.get("feeds", {}))

    # Rare low-cost holy-grail attempt: known Anchor pattern for distributed audio podcast RSS.
    anchor_rss = _discover_anchor_rss(show)
    if anchor_rss:
        rss_list = _ensure_rss_list(feeds)
        if anchor_rss not in rss_list:
            rss_list.insert(0, anchor_rss)
        feeds["rss"] = rss_list

    handle = show.get("youtube_handle")
    channel_url = show.get("youtube_channel_url")
    if handle or channel_url:
        channel_id = discover_youtube_channel_id(channel_url or handle)
        feeds["youtube"] = youtube_rss_for_channel_id(channel_id)
        feeds["youtube_channel_id"] = channel_id

    # normalize/dedupe RSS list
    if "rss" in feeds:
        seen: set[str] = set()
        deduped: list[str] = []
        for rss_url in _ensure_rss_list(feeds):
            if rss_url not in seen:
                deduped.append(rss_url)
                seen.add(rss_url)
        feeds["rss"] = deduped

    return feeds
