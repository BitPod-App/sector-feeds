from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bitpod.paths import RETROSPECTIVE_FLAG_QUEUE_PATH


def load_flag_entries(path: Path = RETROSPECTIVE_FLAG_QUEUE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL in {path} at line {lineno}: {exc.msg}") from exc
        if not isinstance(obj, dict):
            raise ValueError(f"Invalid JSONL in {path} at line {lineno}: expected object")
        entries.append(obj)
    return entries


def summarize_flag_entries(entries: list[dict[str, Any]], limit: int = 10) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be >= 1")

    open_count = sum(1 for e in entries if e.get("status") == "open")
    closed_count = sum(1 for e in entries if e.get("status") == "closed")
    recent = entries[-limit:]

    return {
        "total": len(entries),
        "open": open_count,
        "closed": closed_count,
        "recent": recent,
    }
