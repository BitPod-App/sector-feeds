#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/check_bitregime_core_intake_handshake.sh <intake_json_path> <deck_id> [output_json_path]

Examples:
  bash scripts/check_bitregime_core_intake_handshake.sh \
    ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
    deck_weekly_btc

  bash scripts/check_bitregime_core_intake_handshake.sh \
    ../bitregime-core/artifacts/intake/jack_mallers_show_intake.json \
    deck_weekly_btc \
    artifacts/coordination/bitregime_intake_handshake_jack_mallers_show_deck_weekly_btc.json
USAGE
}

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  usage
  exit 2
fi

INTAKE_JSON="$1"
DECK_ID="$2"
OUTPUT_JSON="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$INTAKE_JSON" "$DECK_ID" "$OUTPUT_JSON" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

from bitpod.core_intake_handshake import (
    compatibility_policy,
    load_payload,
    payload_fingerprint_sha256,
    pending_for_deck,
    validate_payload,
)

intake_path = Path(sys.argv[1]).expanduser().resolve()
deck_id = sys.argv[2]
output_raw = sys.argv[3].strip()

errors: list[str] = []
payload = {}
if not intake_path.exists():
    errors.append(f"missing_file:intake_json:{intake_path}")
else:
    payload = load_payload(intake_path)
    if not payload:
        errors.append(f"invalid_json:intake_json:{intake_path}")
    errors.extend(validate_payload(payload))

pending = pending_for_deck(payload, deck_id=deck_id) if not errors else []
fingerprint = payload_fingerprint_sha256(payload) if payload else None

out = {
    "validator_version": compatibility_policy()["validator_version"],
    "compatibility_policy": compatibility_policy(),
    "intake_json_path": str(intake_path),
    "payload_fingerprint_sha256": fingerprint,
    "deck_id": deck_id,
    "contract_ok": not errors,
    "contract_errors": sorted(errors),
    "contract_version": payload.get("contract_version"),
    "sector_feed_id": payload.get("sector_feed_id"),
    "sector_feed_source_id": payload.get("sector_feed_source_id"),
    "episode_count": len(payload.get("episodes") or []) if isinstance(payload.get("episodes"), list) else 0,
    "pending_count": len(pending),
    "pending": pending,
}

if output_raw:
    output_path = Path(output_raw).expanduser().resolve()
else:
    sector = str(payload.get("sector_feed_id") or "unknown_feed").strip() or "unknown_feed"
    output_path = (
        Path.cwd()
        / "artifacts"
        / "coordination"
        / f"bitregime_intake_handshake_{sector}_{deck_id}.json"
    )

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"output_path": str(output_path), "contract_ok": out["contract_ok"], "pending_count": out["pending_count"]}, indent=2))
if errors and errors[0].startswith("missing_file:intake_json:"):
    print("hint=produce the intake artifact in bitregime-core first, then rerun this check")
raise SystemExit(0 if out["contract_ok"] else 1)
PY
