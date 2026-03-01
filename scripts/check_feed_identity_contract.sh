#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" <<'PY'
import json
import re
import sys
from pathlib import Path

show_key = sys.argv[1]
obj = json.loads(Path("shows.json").read_text(encoding="utf-8"))
show = ((obj.get("shows") or {}).get(show_key) or {})
if not show:
    raise SystemExit(f"Unknown show_key: {show_key}")

sector_feed_id = str(show.get("sector_feed_id") or "").strip()
sector_feed_source_id = str(show.get("sector_feed_source_id") or "").strip()
catalog_permalink_path = str(show.get("catalog_permalink_path") or "").strip()

errors = []
if not sector_feed_id:
    errors.append("missing:sector_feed_id")
if not sector_feed_source_id:
    errors.append("missing:sector_feed_source_id")
if not catalog_permalink_path:
    errors.append("missing:catalog_permalink_path")
else:
    expected = f"/antenna/sector-feeds/{sector_feed_id or '<missing>'}"
    if catalog_permalink_path != expected:
        errors.append(f"invalid:catalog_permalink_path expected={expected} actual={catalog_permalink_path}")
if sector_feed_id and not re.fullmatch(r"[a-z0-9_]+", sector_feed_id):
    errors.append("invalid:sector_feed_id_format")

print(f"show_key={show_key}")
print(f"sector_feed_id={sector_feed_id}")
print(f"sector_feed_source_id={sector_feed_source_id}")
print(f"catalog_permalink_path={catalog_permalink_path}")
if errors:
    for item in errors:
        print(f"check=FAIL {item}")
    print("feed_identity_contract=FAIL")
    raise SystemExit(1)
print("check=PASS required_ids_and_path")
print("feed_identity_contract=PASS")
PY
