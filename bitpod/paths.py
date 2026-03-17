import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Union

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("BITPOD_ROOT", _DEFAULT_ROOT)).resolve()
CONFIG_PATH = ROOT / "shows.json"
INDEX_PATH = ROOT / "index" / "processed.json"
DECK_STATE_PATH = ROOT / "index" / "deck_state.json"
TRANSCRIPTS_ROOT = ROOT / "transcripts"
_UTC_MONTH = datetime.now(timezone.utc).strftime("%Y-%m")
RETRO_FLAG_QUEUE_PATH = ROOT / "artifacts" / "coordination" / f"retro_flag_queue_{_UTC_MONTH}.jsonl"
_ROOTED_PATH_MARKERS = ("transcripts", "cache", "artifacts", "index")


def resolve_repo_path(raw_path: Optional[Union[str, os.PathLike[str]]], root: Optional[Path] = None) -> Optional[Path]:
    if raw_path is None:
        return None

    resolved_root = ROOT if root is None else root
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        return (resolved_root / path).resolve(strict=False)
    if path.exists():
        return path

    parts = path.parts
    for marker in _ROOTED_PATH_MARKERS:
        if marker in parts:
            idx = parts.index(marker)
            return (resolved_root / Path(*parts[idx:])).resolve(strict=False)

    if path.name == "shows.json":
        return (resolved_root / "shows.json").resolve(strict=False)
    return path
