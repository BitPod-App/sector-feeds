#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key>"
  exit 2
fi

SHOW_KEY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

python3 - "$SHOW_KEY" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

from datetime import datetime, timezone

from bitpod.storage import write_gpt_review_artifact, write_gpt_review_request

show_key = sys.argv[1]
repo_root = Path(sys.argv[2])
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
if not show:
    raise SystemExit(f"Unknown show_key: {show_key}")

stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
status_basename = Path(stable_pointer).stem + "_status"
status_json = repo_root / "transcripts" / show_key / f"{Path(stable_pointer).stem}_status.json"
if not status_json.exists():
    raise SystemExit(f"Missing status artifact: {status_json}")

payload = json.loads(status_json.read_text(encoding="utf-8"))
review_path = write_gpt_review_request(show_key=show_key, payload=payload, status_basename=status_basename)
artifact_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
payload["gpt_review_request_path"] = str(review_path)
artifact_path = write_gpt_review_artifact(show_key=show_key, payload=payload, artifact_tag=artifact_tag)
print(f"gpt_review_request_path={review_path}")
print(f"gpt_review_artifact_path={artifact_path}")
PY
