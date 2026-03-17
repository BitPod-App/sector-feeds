#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from bitpod.storage import render_public_landing_page, _bundle_verification_mode

ARTIFACT_RULES = {
    "status.json": {"must_contain": "public_permalink_status.v1"},
    "discovery.json": {"must_contain": "public_permalink_discovery.v1"},
    "intake.md": {"must_contain": "# Transcript Intake"},
    "transcript.md": {"must_not_be_empty": True},
}


def _status_path(repo_root: Path, show_key: str, stable_pointer: str) -> Path:
    return repo_root / "transcripts" / show_key / f"{Path(stable_pointer).stem}_status.json"


def _fetch(url: str, timeout: float) -> tuple[int | None, str | None, str]:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/markdown,text/plain,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310
            body = resp.read().decode("utf-8", errors="ignore")
            return getattr(resp, "status", 200), resp.headers.get("Content-Type"), body
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type"), exc.read().decode("utf-8", errors="ignore")
    except URLError:
        return None, None, ""


def _probe(url: str, artifact_name: str, timeout: float, retries: int, delay: float) -> dict[str, Any]:
    rule = ARTIFACT_RULES[artifact_name]
    last_status: int | None = None
    last_content_type: str | None = None
    for attempt in range(retries):
        status, content_type, body = _fetch(url, timeout)
        last_status = status
        last_content_type = content_type
        readable = status == 200
        if readable and rule.get("must_contain") and rule["must_contain"] not in body:
            readable = False
        if readable and rule.get("must_not_be_empty") and not body.strip():
            readable = False
        if readable:
            return {
                "url": url,
                "http_status": status,
                "content_type": content_type,
                "readable": True,
                "verified_via": "public_http",
            }
        if attempt + 1 < retries:
            time.sleep(delay)
    return {
        "url": url,
        "http_status": last_status,
        "content_type": last_content_type,
        "readable": False,
        "verified_via": "public_http",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deployed public permalink readability and write health into status artifacts.")
    parser.add_argument("--show", dest="show_key", default="jack_mallers_show")
    parser.add_argument("--base-url", dest="base_url", default=None)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--retry-delay", type=float, default=2.0)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = REPO_ROOT
    shows_payload = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
    show = (((shows_payload or {}).get("shows") or {}).get(args.show_key) or {})
    if not show:
        raise SystemExit(f"Unknown show_key: {args.show_key}")

    stable_pointer = str(show.get("stable_pointer") or ("jack_mallers.md" if args.show_key == "jack_mallers_show" else "latest_bitpod.md"))
    local_status_path = _status_path(repo_root, args.show_key, stable_pointer)
    if not local_status_path.exists():
        raise SystemExit(f"Missing local status: {local_status_path}")

    local_status = json.loads(local_status_path.read_text(encoding="utf-8"))
    permalink_id = local_status.get("public_permalink_id")
    if not permalink_id:
        raise SystemExit("Missing public_permalink_id in local status payload")

    base_url = (args.base_url or "").strip().rstrip("/")
    if not base_url:
        status_url = str(local_status.get("public_permalink_status_url") or "").strip()
        if status_url.endswith("/status.json"):
            base_url = status_url.rsplit("/", 1)[0]
    elif base_url.endswith("/status.json"):
        base_url = base_url.rsplit("/", 1)[0]
    elif not base_url.endswith(f"/{permalink_id}"):
        base_url = f"{base_url}/{permalink_id}"
    if not base_url:
        raise SystemExit("Could not determine public base URL")

    readability: dict[str, Any] = {}
    missing: list[str] = []
    for artifact_name in ("status.json", "intake.md", "transcript.md", "discovery.json"):
        url = f"{base_url}/{artifact_name}"
        result = _probe(url, artifact_name, args.timeout, args.retries, args.retry_delay)
        readability[artifact_name] = result
        if not result["readable"]:
            missing.append(artifact_name)

    health = {
        "public_bundle_complete": len(missing) == 0,
        "public_bundle_readability": readability,
        "public_bundle_missing": missing,
        "public_bundle_verification_mode": _bundle_verification_mode(readability),
        "public_bundle_verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if args.write:
        public_status_path = Path(local_status["public_permalink_status_path"])
        public_status = json.loads(public_status_path.read_text(encoding="utf-8"))
        public_status.update(health)
        public_status_path.write_text(json.dumps(public_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        render_public_landing_page(
            public_status=public_status,
            landing_path=Path(local_status["public_permalink_landing_path"]),
            base_url=base_url.rsplit("/", 1)[0] if base_url.endswith(f"/{permalink_id}") else base_url,
        )

        local_status.update(health)
        local_status_path.write_text(json.dumps(local_status, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "show_key": args.show_key,
                "public_id": permalink_id,
                "base_url": base_url,
                **health,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if health["public_bundle_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
REPO_ROOT = Path(__file__).resolve().parents[1]
