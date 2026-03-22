from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib

from bitpod.paths import INDEX_PATH, relativize_repo_path, resolve_repo_path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_processed(path: Path = INDEX_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"episodes": {}}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("episodes", {})
    for payload in (data.get("episodes") or {}).values():
        if not isinstance(payload, dict):
            continue
        for key, value in list(payload.items()):
            if key.endswith("_path") and isinstance(value, str) and value:
                payload[key] = str(resolve_repo_path(value))
    return data


def save_processed(index: dict[str, Any], path: Path = INDEX_PATH) -> None:
    serialized = json.loads(json.dumps(index))
    for payload in (serialized.get("episodes") or {}).values():
        if not isinstance(payload, dict):
            continue
        for key, value in list(payload.items()):
            if key.endswith("_path") and isinstance(value, str) and value:
                payload[key] = relativize_repo_path(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(serialized, handle, indent=2, sort_keys=True)
        handle.write("\n")


def episode_key(show_key: str, guid_or_link: str) -> str:
    return f"{show_key}::{guid_or_link}"


def canonical_episode_id(sector_feed_id: str, feed_episode_id: str) -> str:
    raw = f"{sector_feed_id}::{feed_episode_id}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:16]
