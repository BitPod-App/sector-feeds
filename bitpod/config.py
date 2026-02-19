from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bitpod.paths import CONFIG_PATH

DEFAULT_SHOWS: dict[str, dict[str, Any]] = {
    "jack_mallers_show": {
        "show_key": "jack_mallers_show",
        "youtube_handle": "@thejackmallersshow",
        "youtube_channel_url": "https://youtube.com/@thejackmallersshow",
        "stable_pointer": "mallers_bitpod.md",
        "anchor_show_id": "e29097f4",
        "discover_anchor_holy_grail": True,
        "feeds": {
            "rss": ["https://anchor.fm/s/e29097f4/podcast/rss"],
        },
    }
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"shows": DEFAULT_SHOWS.copy()}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("shows", {})
    for show_key, show in DEFAULT_SHOWS.items():
        data["shows"].setdefault(show_key, show)
    return data


def save_config(config: dict[str, Any], path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, sort_keys=True)
        handle.write("\n")


def get_show(config: dict[str, Any], show_key: str) -> dict[str, Any]:
    show = config.get("shows", {}).get(show_key)
    if not show:
        raise KeyError(f"Unknown show: {show_key}")
    return show
