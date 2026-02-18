from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bitpod.indexer import episode_key, load_processed, now_iso, save_processed

LOGGER = logging.getLogger(__name__)


def _mark(index: dict[str, Any], key: str, status: str, **kwargs: Any) -> None:
    payload = {"status": status, "updated_at": now_iso(), **kwargs}
    index["episodes"][key] = payload


def get_feed_urls(show: dict[str, Any]) -> list[str]:
    feeds = show.get("feeds", {})
    urls: list[str] = []

    youtube_feed = feeds.get("youtube")
    if youtube_feed:
        urls.append(str(youtube_feed))

    rss_feeds = feeds.get("rss")
    if isinstance(rss_feeds, str) and rss_feeds:
        urls.append(rss_feeds)
    if isinstance(rss_feeds, list):
        urls.extend([str(url) for url in rss_feeds if url])

    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
    return deduped


def filter_episodes(episodes: list[Any], max_episodes: int = 3, since_days: int | None = None) -> list[Any]:
    ordered = sorted(episodes, key=lambda ep: ep.published_at, reverse=True)
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        ordered = [ep for ep in ordered if ep.published_at >= cutoff]
    return ordered[:max_episodes]


def sync_show(
    show: dict[str, Any],
    model: str = "gpt-4o-mini-transcribe",
    max_episodes: int = 3,
    since_days: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    show_key = show["show_key"]
    feed_urls = get_feed_urls(show)

    stats: dict[str, Any] = {
        "seen": 0,
        "selected": 0,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "dry_run": dry_run,
        "feeds": feed_urls,
    }

    if not feed_urls:
        if dry_run:
            stats["would_process"] = []
            stats["note"] = "No feeds configured yet. Run discover first."
            return stats
        raise RuntimeError(f"No feed URL found for show {show_key}. Run discover first.")

    index = load_processed()

    from bitpod.feeds import parse_feed

    episodes: list[Any] = []
    for feed_url in feed_urls:
        episodes.extend(parse_feed(feed_url))

    deduped_by_guid: dict[str, Any] = {}
    for episode in episodes:
        deduped_by_guid[str(episode.guid)] = episode
    episodes = list(deduped_by_guid.values())

    stats["seen"] = len(episodes)
    selected = filter_episodes(episodes, max_episodes=max_episodes, since_days=since_days)
    stats["selected"] = len(selected)

    if dry_run:
        stats["would_process"] = [
            {
                "title": ep.title,
                "published_at": ep.published_at.isoformat(),
                "source_url": ep.source_url,
                "feed_url": ep.feed_url,
                "source_type": getattr(ep, "source_type", "unknown"),
            }
            for ep in selected
        ]
        return stats

    for episode in selected:
        key = episode_key(show_key, episode.guid)
        existing = index["episodes"].get(key)
        if existing and existing.get("status") == "ok":
            stats["skipped"] += 1
            continue

        LOGGER.info("Processing: %s", episode.title)
        try:
            _process_episode(show_key, episode, index, key, model=model)
            stats["processed"] += 1
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed episode %s: %s", episode.source_url, exc)
            _mark(index, key, "failed", reason=str(exc), source_url=episode.source_url)
            stats["failed"] += 1
        finally:
            save_processed(index)

    return stats


def _process_episode(show_key: str, episode: Any, index: dict[str, Any], key: str, model: str) -> None:
    with tempfile.TemporaryDirectory(prefix="bitpod-") as tmp:
        from bitpod.audio import acquire_media
        from bitpod.storage import write_transcript
        from bitpod.transcribe import transcribe_audio

        media_path = acquire_media(episode, Path(tmp))
        result = transcribe_audio(media_path, model=model)
        transcript_file = write_transcript(
            show_key=show_key,
            episode_title=episode.title,
            published_at=episode.published_at,
            source_url=episode.source_url,
            guid=episode.guid,
            transcript_text=result.text,
            transcription_model=result.model_used,
            segments=result.segments,
        )
        _mark(
            index,
            key,
            "ok",
            transcript_path=str(transcript_file),
            source_url=episode.source_url,
            published_at=episode.published_at.isoformat(),
            transcription_model=result.model_used,
            source_type=getattr(episode, "source_type", "unknown"),
            media_url=getattr(episode, "media_url", None),
        )
