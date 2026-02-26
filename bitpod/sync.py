from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bitpod.indexer import episode_key, load_processed, now_iso, save_processed
from bitpod.paths import ROOT, TRANSCRIPTS_ROOT

LOGGER = logging.getLogger(__name__)

SOURCE_RANK = {
    "rss_audio": 0,
    "rss_video": 1,
    "rss_media": 2,
    "youtube_video": 3,
    "rss_link": 4,
    "unknown": 5,
}
LIVE_YOUTUBE_TITLE_PATTERN = re.compile(r"\b(live|upcoming|premiere)\b", re.IGNORECASE)


@dataclass
class ProcessingError(RuntimeError):
    stage: str
    reason: str

    def __post_init__(self) -> None:
        super().__init__(f"{self.stage}: {self.reason}")


def _mark(index: dict[str, Any], key: str, status: str, **kwargs: Any) -> None:
    payload = {"status": status, "updated_at": now_iso(), **kwargs}
    index["episodes"][key] = payload


def _source_rank(source_type: str) -> int:
    return SOURCE_RANK.get(source_type, SOURCE_RANK["unknown"])


def _cache_key(show_key: str, guid: str) -> str:
    payload = f"{show_key}::{guid}".encode("utf-8", errors="ignore")
    return hashlib.sha1(payload).hexdigest()[:16]


def _next_action_for_stage(stage: str | None) -> str:
    mapping = {
        "discovery": "Run discover and verify feed URLs in shows.json.",
        "caption_quality_gate": "Lower --min-caption-words or allow media fallback.",
        "media_download": "Verify source media URL reachability and retry sync.",
        "transcription": "Check OpenAI key/quota/model availability and retry.",
        "write_output": "Check filesystem permissions and available disk space.",
        "sync": "Inspect logs and rerun sync for jack_mallers_show.",
    }
    if stage and stage in mapping:
        return mapping[stage]
    return "Rerun sync and inspect the show status markdown artifact for details."


def _is_live_like_youtube_episode(episode: Any) -> bool:
    source_type = str(getattr(episode, "source_type", "unknown"))
    if not source_type.startswith("youtube"):
        return False
    title = str(getattr(episode, "title", "") or "")
    return bool(LIVE_YOUTUBE_TITLE_PATTERN.search(title))


def _status_basename(show: dict[str, Any]) -> str:
    stable_name = _stable_pointer_name(show)
    stem = Path(stable_name).stem
    return f"{stem}_status"


def get_feed_urls(show: dict[str, Any]) -> list[str]:
    feeds = show.get("feeds", {})
    urls: list[str] = []

    # Prefer RSS first when available (usually cheaper for audio-first ingestion).
    rss_feeds = feeds.get("rss")
    if isinstance(rss_feeds, str) and rss_feeds:
        urls.append(rss_feeds)
    if isinstance(rss_feeds, list):
        urls.extend([str(url) for url in rss_feeds if url])

    youtube_feed = feeds.get("youtube")
    if youtube_feed:
        urls.append(str(youtube_feed))

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


def _choose_best_source(existing: Any, candidate: Any) -> Any:
    existing_rank = _source_rank(str(getattr(existing, "source_type", "unknown")))
    candidate_rank = _source_rank(str(getattr(candidate, "source_type", "unknown")))
    if candidate_rank < existing_rank:
        return candidate
    if candidate_rank > existing_rank:
        return existing

    if getattr(candidate, "published_at", datetime.min) >= getattr(existing, "published_at", datetime.min):
        return candidate
    return existing


def sync_show(
    show: dict[str, Any],
    model: str = "gpt-4o-mini-transcribe",
    max_episodes: int = 3,
    since_days: int | None = None,
    dry_run: bool = False,
    source_policy: str = "balanced",
    no_youtube_download: bool = False,
    min_caption_words: int = 120,
    min_episode_age_minutes: int = 180,
    as_of_utc: datetime | None = None,
) -> dict[str, Any]:
    from bitpod.storage import (
        write_gpt_review_request,
        write_public_permalink_artifacts,
        write_run_status_artifacts,
    )

    show_key = show["show_key"]
    run_started_at = now_iso()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    feed_urls = get_feed_urls(show)

    stats: dict[str, Any] = {
        "seen": 0,
        "selected": 0,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "caption_used": 0,
        "dry_run": dry_run,
        "feeds": feed_urls,
        "source_policy": source_policy,
        "min_episode_age_minutes": min_episode_age_minutes,
    }

    # Always produce explicit status artifacts for non-dry runs.
    status_basename = _status_basename(show)
    status_payload: dict[str, Any] = {
        "show_key": show_key,
        "run_id": run_id,
        "run_started_at_utc": run_started_at,
        "run_finished_at_utc": None,
        "run_status": "failed",
        "latest_episode_guid": None,
        "latest_episode_title": None,
        "latest_episode_published_at_utc": None,
        "attempted_episode_guid": None,
        "attempted_episode_title": None,
        "attempted_source_type": None,
        "attempted_source_url": None,
        "included_in_pointer": False,
        "pointer_path": str(TRANSCRIPTS_ROOT / show_key / _stable_pointer_name(show)),
        "pointer_updated_at_utc": None,
        "plain_artifact_path": None,
        "segments_artifact_path": None,
        "public_permalink_id": None,
        "public_permalink_latest_path": None,
        "public_permalink_status_path": None,
        "public_permalink_manifest_path": None,
        "failure_stage": None,
        "failure_reason": None,
        "suggested_next_action": None,
    }

    if not feed_urls:
        if dry_run:
            stats["would_process"] = []
            stats["note"] = "No feeds configured yet. Run discover first."
            return stats
        status_payload["failure_stage"] = "discovery"
        status_payload["failure_reason"] = "No feed URL found. Run discover first."
        status_payload["suggested_next_action"] = _next_action_for_stage("discovery")
        status_payload["run_finished_at_utc"] = now_iso()
        status_json_path, status_md_path = write_run_status_artifacts(
            show_key=show_key,
            payload=status_payload,
            status_basename=status_basename,
        )
        status_payload["status_json_path"] = str(status_json_path)
        status_payload["status_md_path"] = str(status_md_path)
        review_path = write_gpt_review_request(show_key=show_key, payload=status_payload, status_basename=status_basename)
        status_payload["gpt_review_request_path"] = str(review_path)
        public_paths = write_public_permalink_artifacts(show_key=show_key, status_payload=status_payload)
        status_payload.update(public_paths)
        write_run_status_artifacts(
            show_key=show_key,
            payload=status_payload,
            status_basename=status_basename,
        )
        raise RuntimeError(f"No feed URL found for show {show_key}. Run discover first.")

    index = load_processed()

    from bitpod.feeds import parse_feed

    episodes: list[Any] = []
    for feed_url in feed_urls:
        episodes.extend(parse_feed(feed_url))

    deduped_by_guid: dict[str, Any] = {}
    for episode in episodes:
        guid = str(episode.guid)
        current = deduped_by_guid.get(guid)
        deduped_by_guid[guid] = episode if current is None else _choose_best_source(current, episode)

    episodes = list(deduped_by_guid.values())
    cutoff_now = as_of_utc or datetime.now(timezone.utc)
    episodes = [ep for ep in episodes if ep.published_at <= cutoff_now]
    stats["seen"] = len(episodes)

    # Live streams and very fresh uploads can be incomplete; hold recent YouTube episodes by default.
    mature_cutoff = cutoff_now - timedelta(minutes=max(min_episode_age_minutes, 0))
    matured_episodes: list[Any] = []
    deferred_recent_youtube = 0
    deferred_live_youtube = 0
    for ep in episodes:
        source_type = str(getattr(ep, "source_type", "unknown"))
        if _is_live_like_youtube_episode(ep):
            deferred_live_youtube += 1
            continue
        if source_type.startswith("youtube") and ep.published_at > mature_cutoff:
            deferred_recent_youtube += 1
            continue
        matured_episodes.append(ep)

    stats["deferred_recent_youtube"] = deferred_recent_youtube
    stats["deferred_live_youtube"] = deferred_live_youtube
    selected = filter_episodes(matured_episodes, max_episodes=max_episodes, since_days=since_days)
    stats["selected"] = len(selected)

    if dry_run:
        stats["would_process"] = [
            {
                "title": ep.title,
                "published_at": ep.published_at.isoformat(),
                "source_url": ep.source_url,
                "feed_url": ep.feed_url,
                "source_type": getattr(ep, "source_type", "unknown"),
                "source_rank": _source_rank(str(getattr(ep, "source_type", "unknown"))),
            }
            for ep in selected
        ]
        return stats

    latest_episode = selected[0] if selected else None
    attempted_episode = latest_episode
    latest_episode_succeeded = False

    if latest_episode is not None:
        status_payload["latest_episode_guid"] = str(latest_episode.guid)
        status_payload["latest_episode_title"] = latest_episode.title
        status_payload["latest_episode_published_at_utc"] = latest_episode.published_at.isoformat()

    if not selected:
        status_payload["failure_stage"] = "discovery"
        if deferred_recent_youtube > 0:
            status_payload["failure_reason"] = (
                f"No eligible episodes yet; deferred {deferred_recent_youtube} recent YouTube item(s) "
                f"under min_episode_age_minutes={min_episode_age_minutes}."
            )
        else:
            status_payload["failure_reason"] = "No episodes selected under current filters and maturity guard."
        status_payload["suggested_next_action"] = _next_action_for_stage("discovery")

    for episode in selected:
        key = episode_key(show_key, episode.guid)
        existing = index["episodes"].get(key)
        if existing and existing.get("status") == "ok":
            stats["skipped"] += 1
            if latest_episode and str(episode.guid) == str(latest_episode.guid):
                latest_episode_succeeded = True
            continue

        status_payload["attempted_episode_guid"] = str(episode.guid)
        status_payload["attempted_episode_title"] = episode.title
        status_payload["attempted_source_type"] = getattr(episode, "source_type", "unknown")
        status_payload["attempted_source_url"] = episode.source_url
        LOGGER.info("Processing: %s", episode.title)
        try:
            used_caption = _process_episode(
                show=show,
                show_key=show_key,
                episode=episode,
                index=index,
                key=key,
                model=model,
                existing=existing,
                source_policy=source_policy,
                no_youtube_download=no_youtube_download,
                min_caption_words=min_caption_words,
            )
            stats["processed"] += 1
            if used_caption:
                stats["caption_used"] += 1
            if latest_episode and str(episode.guid) == str(latest_episode.guid):
                latest_episode_succeeded = True
        except ProcessingError as exc:
            LOGGER.exception("Failed episode %s: %s", episode.source_url, exc)
            _mark(index, key, "failed", reason=exc.reason, stage=exc.stage, source_url=episode.source_url)
            stats["failed"] += 1
            status_payload["failure_stage"] = exc.stage
            status_payload["failure_reason"] = exc.reason
            status_payload["suggested_next_action"] = _next_action_for_stage(exc.stage)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Failed episode %s: %s", episode.source_url, exc)
            _mark(index, key, "failed", reason=str(exc), stage="sync", source_url=episode.source_url)
            stats["failed"] += 1
            status_payload["failure_stage"] = "sync"
            status_payload["failure_reason"] = str(exc)
            status_payload["suggested_next_action"] = _next_action_for_stage("sync")
        finally:
            save_processed(index)

    if latest_episode_succeeded:
        _refresh_stable_pointer(show, index)
        status_payload["included_in_pointer"] = True
        status_payload["pointer_updated_at_utc"] = now_iso()
        status_payload["run_status"] = "ok"
    else:
        status_payload["included_in_pointer"] = False
        status_payload["run_status"] = "failed" if stats["failed"] > 0 or selected else "failed"
        if not status_payload["failure_stage"]:
            status_payload["failure_stage"] = "sync"
            status_payload["failure_reason"] = "Latest episode was not included in pointer update."
            status_payload["suggested_next_action"] = _next_action_for_stage("sync")

    if latest_episode is not None:
        latest_key = episode_key(show_key, latest_episode.guid)
        latest_payload = index["episodes"].get(latest_key, {})
        status_payload["plain_artifact_path"] = latest_payload.get("transcript_plain_path")
        status_payload["segments_artifact_path"] = latest_payload.get("transcript_segments_path")
        if status_payload["attempted_episode_guid"] is None:
            status_payload["attempted_episode_guid"] = str(latest_episode.guid)
            status_payload["attempted_episode_title"] = latest_episode.title
            status_payload["attempted_source_type"] = getattr(latest_episode, "source_type", "unknown")
            status_payload["attempted_source_url"] = latest_episode.source_url

    status_payload["run_finished_at_utc"] = now_iso()
    status_json_path, status_md_path = write_run_status_artifacts(
        show_key=show_key,
        payload=status_payload,
        status_basename=status_basename,
    )
    status_payload["status_json_path"] = str(status_json_path)
    status_payload["status_md_path"] = str(status_md_path)
    review_path = write_gpt_review_request(show_key=show_key, payload=status_payload, status_basename=status_basename)
    status_payload["gpt_review_request_path"] = str(review_path)
    public_paths = write_public_permalink_artifacts(show_key=show_key, status_payload=status_payload)
    status_payload.update(public_paths)
    # Persist paths in JSON status too.
    status_json_path, status_md_path = write_run_status_artifacts(
        show_key=show_key,
        payload=status_payload,
        status_basename=status_basename,
    )
    stats["status_json_path"] = str(status_json_path)
    stats["status_md_path"] = str(status_md_path)
    stats["gpt_review_request_path"] = str(review_path)
    stats["latest_included_in_pointer"] = bool(status_payload["included_in_pointer"])
    stats["run_status"] = status_payload["run_status"]
    return stats


def _maybe_use_captions(
    *,
    show_key: str,
    episode: Any,
    index: dict[str, Any],
    key: str,
    min_caption_words: int,
) -> bool:
    from bitpod.audio import extract_youtube_caption_payload
    from bitpod.storage import write_output_artifacts, write_transcript

    caption_dir = ROOT / "cache" / "captions" / show_key / _cache_key(show_key, str(episode.guid))
    payload = extract_youtube_caption_payload(str(episode.source_url), caption_dir, min_words=min_caption_words)
    if not payload:
        return False

    segments = [
        {
            "start": cue.start,
            "end": cue.end,
            "text": cue.text,
            "speaker": "unknown",
            "source": "youtube_caption",
        }
        for cue in payload.cues
    ]

    try:
        transcript_file = write_transcript(
            show_key=show_key,
            episode_title=episode.title,
            published_at=episode.published_at,
            source_url=episode.source_url,
            guid=episode.guid,
            transcript_text=payload.text,
            transcription_model="youtube_caption_auto",
            segments=segments,
            transcript_source="youtube_caption",
            speaker_strategy="unknown",
        )
        plain_path, segments_path = write_output_artifacts(
            transcript_file=transcript_file,
            transcript_text=payload.text,
            segments=segments,
            metadata={
                "source_platform": "youtube",
                "source_url": episode.source_url,
                "source_id": str(episode.guid),
                "show_name": show_key,
                "episode_title": episode.title,
                "published_at_utc": episode.published_at.isoformat(),
                "retrieved_at_utc": now_iso(),
                "pipeline_version": "0.2.1.1",
                "transcription_method": "youtube_captions_stitched",
                "speaker_mode": "unknown",
                "speakers_detected": "unknown",
                "quality_word_count": payload.quality.get("word_count", 0),
                "quality_repetition_ratio_5gram": payload.quality.get("repetition_ratio_5gram", 0),
                "quality_lexical_diversity": payload.quality.get("lexical_diversity", 0),
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise ProcessingError(stage="write_output", reason=str(exc)) from exc

    _mark(
        index,
        key,
        "ok",
        transcript_path=str(transcript_file),
        transcript_plain_path=str(plain_path),
        transcript_segments_path=str(segments_path),
        source_url=episode.source_url,
        published_at=episode.published_at.isoformat(),
        transcription_model="youtube_caption_auto",
        source_type=getattr(episode, "source_type", "unknown"),
        media_url=getattr(episode, "media_url", None),
        source_mode="captions",
        gpt_status="pending",
        gpt_processed_at=None,
    )
    return True


def _resolve_cached_media(existing: dict[str, Any] | None) -> Path | None:
    if not existing:
        return None
    cache_path = existing.get("media_cache_path")
    if isinstance(cache_path, str) and cache_path:
        path = Path(cache_path)
        if path.exists():
            return path
    return None


def _download_media_with_cache(show_key: str, episode: Any) -> Path:
    from bitpod.audio import acquire_media

    media_dir = ROOT / "cache" / "media" / show_key / _cache_key(show_key, str(episode.guid))
    media_dir.mkdir(parents=True, exist_ok=True)
    try:
        return acquire_media(episode, media_dir, filename_hint=_cache_key(show_key, str(episode.guid)))
    except Exception as exc:  # noqa: BLE001
        raise ProcessingError(stage="media_download", reason=str(exc)) from exc


def _process_episode(
    *,
    show: dict[str, Any],
    show_key: str,
    episode: Any,
    index: dict[str, Any],
    key: str,
    model: str,
    existing: dict[str, Any] | None,
    source_policy: str,
    no_youtube_download: bool,
    min_caption_words: int,
) -> bool:
    from bitpod.storage import write_output_artifacts, write_transcript
    from bitpod.transcribe import transcribe_audio

    source_type = str(getattr(episode, "source_type", "unknown"))
    try_captions = source_type.startswith("youtube") and source_policy in {"balanced", "audio-first", "caption-first"}
    caption_used = False

    if try_captions:
        caption_used = _maybe_use_captions(
            show_key=show_key,
            episode=episode,
            index=index,
            key=key,
            min_caption_words=min_caption_words,
        )
        if caption_used:
            return True

    if source_type.startswith("youtube") and no_youtube_download:
        raise ProcessingError(
            stage="caption_quality_gate",
            reason="YouTube download disabled and usable captions were unavailable.",
        )

    media_path = _resolve_cached_media(existing)
    if media_path is None:
        media_path = _download_media_with_cache(show_key, episode)

    try:
        result = transcribe_audio(media_path, model=model)
    except Exception as exc:  # noqa: BLE001
        raise ProcessingError(stage="transcription", reason=str(exc)) from exc

    try:
        transcript_file = write_transcript(
            show_key=show_key,
            episode_title=episode.title,
            published_at=episode.published_at,
            source_url=episode.source_url,
            guid=episode.guid,
            transcript_text=result.text,
            transcription_model=result.model_used,
            segments=result.segments,
            transcript_source="audio_transcription",
            speaker_strategy="guest_priority",
        )
        plain_path, segments_path = write_output_artifacts(
            transcript_file=transcript_file,
            transcript_text=result.text,
            segments=result.segments,
            metadata={
                "source_platform": "rss" if source_type.startswith("rss") else "youtube",
                "source_url": episode.source_url,
                "source_id": str(episode.guid),
                "show_name": show_key,
                "episode_title": episode.title,
                "published_at_utc": episode.published_at.isoformat(),
                "retrieved_at_utc": now_iso(),
                "pipeline_version": "0.2.1.1",
                "transcription_method": f"asr_{result.model_used}",
                "speaker_mode": "unknown",
                "speakers_detected": "unknown",
            },
        )
    except Exception as exc:  # noqa: BLE001
        raise ProcessingError(stage="write_output", reason=str(exc)) from exc

    _mark(
        index,
        key,
        "ok",
        transcript_path=str(transcript_file),
        transcript_plain_path=str(plain_path),
        transcript_segments_path=str(segments_path),
        source_url=episode.source_url,
        published_at=episode.published_at.isoformat(),
        transcription_model=result.model_used,
        source_type=source_type,
        media_url=getattr(episode, "media_url", None),
        media_cache_path=str(media_path),
        source_mode="media",
        gpt_status="pending",
        gpt_processed_at=None,
    )
    return False


def _parse_iso(ts: str | None) -> datetime:
    if not ts:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _stable_pointer_name(show: dict[str, Any]) -> str:
    configured = show.get("stable_pointer")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()
    if show.get("show_key") == "jack_mallers_show":
        return "jack_mallers.md"
    return "latest_bitpod.md"


def _refresh_stable_pointer(show: dict[str, Any], index: dict[str, Any]) -> None:
    show_key = show["show_key"]
    candidates: list[dict[str, Any]] = []
    prefix = f"{show_key}::"

    for key, payload in index.get("episodes", {}).items():
        if not key.startswith(prefix):
            continue
        if payload.get("status") != "ok":
            continue

        transcript_path_raw = payload.get("transcript_path")
        if not isinstance(transcript_path_raw, str) or not transcript_path_raw:
            continue

        transcript_path = Path(transcript_path_raw)
        if not transcript_path.is_absolute():
            transcript_path = ROOT / transcript_path
        if not transcript_path.exists():
            continue

        candidates.append(
            {
                "path": transcript_path,
                "published_at": _parse_iso(payload.get("published_at")),
                "updated_at": _parse_iso(payload.get("updated_at")),
            }
        )

    if not candidates:
        return

    latest = max(candidates, key=lambda item: (item["published_at"], item["updated_at"]))
    source_path = latest["path"]
    pointer_path = TRANSCRIPTS_ROOT / show_key / _stable_pointer_name(show)
    pointer_path.parent.mkdir(parents=True, exist_ok=True)

    text = source_path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    pointer_path.write_text(text, encoding="utf-8")
