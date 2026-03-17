#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
BASE_URL="${2:-${BITPOD_PUBLIC_PERMALINK_BASE_URL:-https://bitpod-public-permalinks.pages.dev}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$SHOW_KEY" "$BASE_URL" <<'PY'
import json
import sys
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import urlopen, Request

show_key, base_url = sys.argv[1], sys.argv[2].rstrip("/")
shows = json.loads(Path("shows.json").read_text(encoding="utf-8"))
show = ((shows or {}).get("shows") or {}).get(show_key) or {}
if not show:
    raise SystemExit(f"Unknown show_key: {show_key}")

status_path = Path("transcripts") / show_key / f"{Path(show.get('stable_pointer') or 'jack_mallers.md').stem}_status.json"
if not status_path.exists():
    raise SystemExit(f"Missing local status file: {status_path}")
status = json.loads(status_path.read_text(encoding="utf-8"))

urls = {
    "transcript": status.get("public_permalink_transcript_url"),
    "status": status.get("public_permalink_status_url"),
    "discovery": status.get("public_permalink_discovery_url"),
}

ok = True
for name, url in urls.items():
    if not url:
        print(f"{name}=FAIL missing_url")
        ok = False
        continue
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(req, timeout=12) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="ignore")
            code = getattr(resp, "status", 200)
    except HTTPError as exc:
        print(f"{name}=FAIL http_{exc.code}")
        ok = False
        continue
    except URLError as exc:
        print(f"{name}=FAIL {exc}")
        ok = False
        continue
    if int(code) != 200:
        print(f"{name}=FAIL http_{code}")
        ok = False
        continue
    if base_url and not str(url).startswith(base_url):
        print(f"{name}=WARN unexpected_base_url expected_prefix={base_url}")
    if name == "status" and "public_permalink_status.v1" not in body:
        print(f"{name}=FAIL missing_contract_marker")
        ok = False
        continue
    if name == "discovery" and "public_permalink_discovery.v1" not in body:
        print(f"{name}=FAIL missing_contract_marker")
        ok = False
        continue
    if name == "transcript" and not body.strip():
        print(f"{name}=FAIL empty_body")
        ok = False
        continue
    print(f"{name}=PASS")

print(f"smoke_public={'PASS' if ok else 'FAIL'}")
raise SystemExit(0 if ok else 1)
PY
