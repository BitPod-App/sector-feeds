#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.storage import _public_permalink_base_url, _public_permalink_id, write_public_permalink_artifacts


def _status_path(repo_root: Path, show_key: str, stable_pointer: str) -> Path:
    return repo_root / "transcripts" / show_key / f"{Path(stable_pointer).stem}_status.json"


def _remote_status_payload(show_key: str) -> dict | None:
    public_id = _public_permalink_id(show_key)
    url = f"{_public_permalink_base_url()}/{public_id}/status.json"
    req = Request(url, headers={"User-Agent": "sector-feeds-refresh-public-permalinks/1.0"})
    try:
        with urlopen(req, timeout=20) as resp:  # nosec B310
            if getattr(resp, "status", 200) != 200:
                return None
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except (HTTPError, URLError, json.JSONDecodeError):
        return None


def main() -> int:
    repo_root = REPO_ROOT
    requested_show = sys.argv[1] if len(sys.argv) > 1 else None
    shows_payload = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
    shows = ((shows_payload or {}).get("shows") or {})
    refreshed = []

    for show_key, show in shows.items():
        if requested_show and show_key != requested_show:
            continue
        stable_pointer = str(show.get("stable_pointer") or ("jack_mallers.md" if show_key == "jack_mallers_show" else "latest_bitpod.md"))
        status_path = _status_path(repo_root, show_key, stable_pointer)
        payload = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else _remote_status_payload(show_key)
        if payload is None:
            continue
        public_paths = write_public_permalink_artifacts(show_key=show_key, status_payload=payload)
        payload.update(public_paths)

        public_status_path = Path(public_paths["public_permalink_status_path"])
        public_status = json.loads(public_status_path.read_text(encoding="utf-8"))
        for key in (
            "public_bundle_complete",
            "public_bundle_readability",
            "public_bundle_missing",
            "public_bundle_verification_mode",
            "public_bundle_verified_at_utc",
        ):
            payload[key] = public_status.get(key)

        status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        refreshed.append(
            {
                "show_key": show_key,
                "run_id": payload.get("run_id"),
                "public_id": public_paths["public_permalink_id"],
                "status_path": str(public_status_path),
            }
        )

    print(json.dumps({"refreshed": refreshed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
