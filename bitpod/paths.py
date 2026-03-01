import os
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("BITPOD_ROOT", _DEFAULT_ROOT)).resolve()
CONFIG_PATH = ROOT / "shows.json"
INDEX_PATH = ROOT / "index" / "processed.json"
DECK_STATE_PATH = ROOT / "index" / "deck_state.json"
TRANSCRIPTS_ROOT = ROOT / "transcripts"
