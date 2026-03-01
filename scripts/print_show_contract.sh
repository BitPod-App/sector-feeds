#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <show_key> [--json]"
}

if [ "$#" -lt 1 ]; then
  usage
  exit 2
fi

SHOW_KEY="$1"
OUTPUT_MODE="text"
shift || true
while [ "$#" -gt 0 ]; do
  case "$1" in
    --json)
      OUTPUT_MODE="json"
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" "$OUTPUT_MODE" <<'PY'
import json
import sys
from pathlib import Path

from bitpod.intake import evaluate_intake_readiness

show_key = sys.argv[1]
output_mode = sys.argv[2]
repo_root = Path(".")
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
if not show:
    raise SystemExit(f"Unknown show_key: {show_key}")

stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_json = repo_root / "transcripts" / show_key / f"{stem}_status.json"
if not status_json.exists():
    raise SystemExit(f"Missing status artifact: {status_json}")

payload = json.loads(status_json.read_text(encoding="utf-8"))
intake = evaluate_intake_readiness(payload)
out = {
    "show_key": show_key,
    "sector_feed_id": show.get("sector_feed_id") or show_key,
    "sector_feed_source_id": show.get("sector_feed_source_id"),
    "catalog_permalink_path": show.get("catalog_permalink_path") or f"/antenna/sector-feeds/{show.get('sector_feed_id') or show_key}",
    "run_status": payload.get("run_status"),
    "ready_via_permalink": bool(payload.get("ready_via_permalink")),
    "intake_ready": bool(intake.get("ok")),
    "public_permalink_transcript_url": payload.get("public_permalink_transcript_url"),
    "public_permalink_status_url": payload.get("public_permalink_status_url"),
    "public_permalink_discovery_url": payload.get("public_permalink_discovery_url"),
}

if output_mode == "json":
    print(json.dumps(out, indent=2, sort_keys=True))
else:
    print(f"show_key={out['show_key']}")
    print(f"sector_feed_id={out['sector_feed_id']}")
    print(f"sector_feed_source_id={out['sector_feed_source_id']}")
    print(f"catalog_permalink_path={out['catalog_permalink_path']}")
    print(f"run_status={out['run_status']}")
    print(f"ready_via_permalink={out['ready_via_permalink']}")
    print(f"intake_ready={out['intake_ready']}")
    print(f"public_permalink_transcript_url={out['public_permalink_transcript_url']}")
    print(f"public_permalink_status_url={out['public_permalink_status_url']}")
    print(f"public_permalink_discovery_url={out['public_permalink_discovery_url']}")
PY
