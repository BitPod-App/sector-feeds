from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib

from bitpod.paths import INDEX_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_processed(path: Path = INDEX_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"episodes": {}}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("episodes", {})
    return data


def save_processed(index: dict[str, Any], path: Path = INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=2, sort_keys=True)
        handle.write("\n")


def episode_key(show_key: str, guid_or_link: str) -> str:
    return f"{show_key}::{guid_or_link}"


def canonical_episode_id(sector_feed_id: str, feed_episode_id: str) -> str:
    raw = f"{sector_feed_id}::{feed_episode_id}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]
