from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("BITPOD_ROOT", _DEFAULT_ROOT)).resolve()
WORKSPACE_ROOT = ROOT.parent
CONFIG_PATH = ROOT / "shows.json"
INDEX_PATH = ROOT / "index" / "processed.json"
DECK_STATE_PATH = ROOT / "index" / "deck_state.json"
TRANSCRIPTS_ROOT = ROOT / "transcripts"
_UTC_MONTH = datetime.now(timezone.utc).strftime("%Y-%m")
RETRO_FLAG_QUEUE_PATH = ROOT / "artifacts" / "coordination" / f"retro_flag_queue_{_UTC_MONTH}.jsonl"


def relativize_repo_path(value: str | Path) -> str:
    path = Path(value).expanduser()
    resolved_root = ROOT.resolve()
    resolved_path = path.resolve(strict=False)
    try:
        return str(resolved_path.relative_to(resolved_root))
    except ValueError:
        return str(path)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return ROOT / path
