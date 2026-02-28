from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bitpod.deck_state import is_consumed
from bitpod.indexer import canonical_episode_id
from bitpod.paths import DECK_STATE_PATH

EXPECTED_CONTRACT_VERSION = "bitregime_core_intake.v1"
SUPPORTED_CONTRACT_VERSIONS = (EXPECTED_CONTRACT_VERSION,)
VALIDATOR_VERSION = "bitpod_intake_handshake_validator.v1"

_TERMINAL_PROCESSING_STATES = {
    "consumed",
    "done",
    "error",
    "failed",
    "processed",
    "skipped",
}

REQUIRED_TOP_LEVEL_FIELDS = (
    "contract_version",
    "sector_feed_id",
    "sector_feed_source_id",
    "episodes",
)

REQUIRED_EPISODE_FIELDS = (
    "feed_episode_id",
    "processing_state.status",
)


def _non_empty(value: Any) -> str:
    text = str(value or "").strip()
    return text


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract_version = _non_empty(payload.get("contract_version"))
    if contract_version != EXPECTED_CONTRACT_VERSION:
        if contract_version in SUPPORTED_CONTRACT_VERSIONS:
            errors.append(f"not_latest_contract_version:{contract_version}")
        else:
            errors.append(f"unsupported_contract_version:{contract_version or '<empty>'}")

    sector_feed_id = _non_empty(payload.get("sector_feed_id"))
    if not sector_feed_id:
        errors.append("missing:sector_feed_id")

    sector_feed_source_id = _non_empty(payload.get("sector_feed_source_id"))
    if not sector_feed_source_id:
        errors.append("missing:sector_feed_source_id")

    episodes = payload.get("episodes")
    if not isinstance(episodes, list):
        return errors + ["missing:episodes"]

    seen: set[str] = set()
    for idx, row in enumerate(episodes):
        if not isinstance(row, dict):
            errors.append(f"invalid_episode:{idx}:not_object")
            continue

        feed_episode_id = _non_empty(row.get("feed_episode_id"))
        if not feed_episode_id:
            errors.append(f"missing:episodes[{idx}].feed_episode_id")
            continue
        if feed_episode_id in seen:
            errors.append(f"duplicate:feed_episode_id:{feed_episode_id}")
        seen.add(feed_episode_id)

        processing_state = row.get("processing_state")
        if not isinstance(processing_state, dict):
            errors.append(f"missing:episodes[{idx}].processing_state")
        elif not _non_empty(processing_state.get("status")):
            errors.append(f"missing:episodes[{idx}].processing_state.status")

    return errors


def payload_fingerprint_sha256(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compatibility_policy() -> dict[str, Any]:
    return {
        "validator_version": VALIDATOR_VERSION,
        "compatibility_mode": "backward_compatible_reader_fail_closed_on_unknown_major",
        "latest_contract_version": EXPECTED_CONTRACT_VERSION,
        "supported_contract_versions": list(SUPPORTED_CONTRACT_VERSIONS),
        "required_top_level_fields": list(REQUIRED_TOP_LEVEL_FIELDS),
        "required_episode_fields": list(REQUIRED_EPISODE_FIELDS),
    }


def pending_for_deck(
    payload: dict[str, Any],
    *,
    deck_id: str,
    deck_state_path: Path = DECK_STATE_PATH,
) -> list[dict[str, Any]]:
    sector_feed_id = _non_empty(payload.get("sector_feed_id"))
    episodes = payload.get("episodes") if isinstance(payload.get("episodes"), list) else []
    rows: list[dict[str, Any]] = []
    for raw in episodes:
        if not isinstance(raw, dict):
            continue
        feed_episode_id = _non_empty(raw.get("feed_episode_id"))
        if not feed_episode_id:
            continue
        status = _non_empty(((raw.get("processing_state") or {}).get("status"))).lower()
        if status in _TERMINAL_PROCESSING_STATES:
            continue
        if is_consumed(deck_id, sector_feed_id, feed_episode_id, path=deck_state_path):
            continue
        rows.append(
            {
                "sector_feed_id": sector_feed_id,
                "sector_feed_source_id": _non_empty(payload.get("sector_feed_source_id")),
                "feed_episode_id": feed_episode_id,
                "canonical_episode_id": _non_empty(raw.get("canonical_episode_id"))
                or canonical_episode_id(sector_feed_id, feed_episode_id),
                "source_episode_id": _non_empty(raw.get("source_episode_id")),
                "published_at_utc": raw.get("published_at_utc"),
                "processing_status": status or "new",
                "title": raw.get("title"),
            }
        )
    rows.sort(key=lambda item: str(item.get("published_at_utc") or ""))
    return rows
