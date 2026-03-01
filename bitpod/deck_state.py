from __future__ import annotations

import json
from typing import Any

from bitpod.indexer import now_iso
from bitpod.paths import DECK_STATE_PATH


def load_deck_state(path=DECK_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "updated_at_utc": None, "decks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at_utc": None, "decks": {}}
    if not isinstance(data, dict):
        return {"version": 1, "updated_at_utc": None, "decks": {}}
    data.setdefault("version", 1)
    data.setdefault("updated_at_utc", None)
    data.setdefault("decks", {})
    return data


def save_deck_state(state: dict[str, Any], path=DECK_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at_utc"] = now_iso()
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_consumed(deck_id: str, sector_feed_id: str, feed_episode_id: str, path=DECK_STATE_PATH) -> bool:
    state = load_deck_state(path=path)
    feed_payload = ((state.get("decks") or {}).get(deck_id) or {}).get(sector_feed_id) or {}
    consumed = set(feed_payload.get("consumed_feed_episode_ids") or [])
    consumed.update(feed_payload.get("consumed_source_episode_ids") or [])
    return feed_episode_id in consumed


def mark_consumed(deck_id: str, sector_feed_id: str, feed_episode_id: str, path=DECK_STATE_PATH) -> dict[str, Any]:
    state = load_deck_state(path=path)
    decks = state.setdefault("decks", {})
    deck_payload = decks.setdefault(deck_id, {})
    feed_payload = deck_payload.setdefault(sector_feed_id, {"consumed_feed_episode_ids": [], "updated_at_utc": None})
    existing = set(feed_payload.get("consumed_feed_episode_ids") or [])
    existing.update(feed_payload.get("consumed_source_episode_ids") or [])
    existing.add(feed_episode_id)
    feed_payload["consumed_feed_episode_ids"] = sorted(existing)
    if "consumed_source_episode_ids" in feed_payload:
        del feed_payload["consumed_source_episode_ids"]
    feed_payload["updated_at_utc"] = now_iso()
    save_deck_state(state, path=path)
    return feed_payload
