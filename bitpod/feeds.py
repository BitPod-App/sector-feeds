from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import feedparser
from dateutil import parser as date_parser


@dataclass
class Episode:
    guid: str
    title: str
    published_at: datetime
    source_url: str
    feed_url: str
    source_type: str = "unknown"
    media_url: str | None = None


def _parse_published(entry: dict[str, Any]) -> datetime:
    if entry.get("published"):
        return date_parser.parse(entry["published"]).astimezone(timezone.utc)
    if entry.get("updated"):
        return date_parser.parse(entry["updated"]).astimezone(timezone.utc)
    if entry.get("published_parsed"):
        return datetime(*entry["published_parsed"][:6], tzinfo=timezone.utc)
    if entry.get("updated_parsed"):
        return datetime(*entry["updated_parsed"][:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _extract_enclosure(entry: dict[str, Any]) -> tuple[str | None, str]:
    enclosures = entry.get("enclosures") or []
    for enclosure in enclosures:
        href = enclosure.get("href")
        media_type = str(enclosure.get("type", ""))
        if not href:
            continue
        if media_type.startswith("audio/"):
            return str(href), "rss_audio"
        if media_type.startswith("video/"):
            return str(href), "rss_video"
    if enclosures:
        href = enclosures[0].get("href")
        if href:
            return str(href), "rss_media"
    return None, "rss_link"


def parse_feed(feed_url: str) -> list[Episode]:
    parsed = feedparser.parse(feed_url)
    episodes: list[Episode] = []
    for entry in parsed.entries:
        guid = entry.get("id") or entry.get("guid") or entry.get("link")
        link = entry.get("link") or guid
        if not guid or not link:
            continue

        media_url, source_type = _extract_enclosure(entry)
        if "youtube.com/feeds/videos.xml" in feed_url:
            source_type = "youtube_video"

        episodes.append(
            Episode(
                guid=str(guid),
                title=str(entry.get("title") or guid),
                published_at=_parse_published(entry),
                source_url=str(link),
                feed_url=feed_url,
                source_type=source_type,
                media_url=media_url,
            )
        )

    episodes.sort(key=lambda ep: ep.published_at)
    return episodes
