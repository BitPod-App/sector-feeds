from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitpod.deck_state import is_consumed
from bitpod.indexer import canonical_episode_id
from bitpod.paths import DECK_STATE_PATH

CONTRACT_VERSION_V1 = "bitregime_core_intake.v1"
CONTRACT_VERSION_V2 = "bitregime_core_intake.v2"
EXPECTED_CONTRACT_VERSION = CONTRACT_VERSION_V2
SUPPORTED_CONTRACT_VERSIONS = (CONTRACT_VERSION_V1, CONTRACT_VERSION_V2)
VALIDATOR_VERSION = "bitpod_intake_handshake_validator.v1"
VALIDATION_OUTPUT_VERSION = "bitpod_intake_handshake_validation_output.v1"
SUPPORTED_VALIDATION_TARGETS = (CONTRACT_VERSION_V1, CONTRACT_VERSION_V2)

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

V2_REQUIRED_TOP_LEVEL_FIELDS = (
    "generated_at_utc",
    "sector_feed_id",
    "sector_feed_source_id",
    "context.deck_id",
    "context.user_id",
    "episodes",
)

V2_REQUIRED_EPISODE_FIELDS = (
    "feed_episode_id",
    "canonical_episode_id",
    "source_episode_id",
    "published_at_utc",
    "title",
    "processing_state.status",
    "processing_state.updated_at_utc",
    "processing_state.first_seen_at_utc",
    "processing_state.attempt_count",
)

V2_ALLOWED_PROCESSING_STATES = {
    "new",
    "pending",
    "queued",
    "processed",
    "consumed",
    "done",
    "failed",
    "error",
    "skipped",
}

_UTC_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def _non_empty(value: Any) -> str:
    text = str(value or "").strip()
    return text


def load_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_utc_iso8601(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if not _UTC_ISO_PATTERN.match(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc


def _validate_payload_v1(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract_version = _non_empty(payload.get("contract_version"))
    if contract_version != CONTRACT_VERSION_V1:
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


def validate_payload_v2(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    contract_version = _non_empty(payload.get("contract_version"))
    if contract_version != CONTRACT_VERSION_V2:
        errors.append(f"unsupported_contract_version:{contract_version or '<empty>'}")

    for field in ("generated_at_utc", "sector_feed_id", "sector_feed_source_id"):
        if not _non_empty(payload.get(field)):
            errors.append(f"missing:{field}")

    context = payload.get("context")
    if not isinstance(context, dict):
        errors.append("missing:context")
        context = {}
    if not _non_empty(context.get("deck_id")):
        errors.append("missing:context.deck_id")
    if not _non_empty(context.get("user_id")):
        errors.append("missing:context.user_id")

    if not _is_utc_iso8601(payload.get("generated_at_utc")):
        errors.append("invalid:generated_at_utc:utc_iso8601")

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
        elif feed_episode_id in seen:
            errors.append(f"duplicate:feed_episode_id:{feed_episode_id}")
        else:
            seen.add(feed_episode_id)

        if not _non_empty(row.get("canonical_episode_id")):
            errors.append(f"missing:episodes[{idx}].canonical_episode_id")
        if not _non_empty(row.get("source_episode_id")):
            errors.append(f"missing:episodes[{idx}].source_episode_id")
        if not _non_empty(row.get("title")):
            errors.append(f"missing:episodes[{idx}].title")

        if not _is_utc_iso8601(row.get("published_at_utc")):
            errors.append(f"invalid:episodes[{idx}].published_at_utc:utc_iso8601")

        processing_state = row.get("processing_state")
        if not isinstance(processing_state, dict):
            errors.append(f"missing:episodes[{idx}].processing_state")
            continue

        status = _non_empty(processing_state.get("status")).lower()
        if not status:
            errors.append(f"missing:episodes[{idx}].processing_state.status")
        elif status not in V2_ALLOWED_PROCESSING_STATES:
            errors.append(f"invalid:episodes[{idx}].processing_state.status:enum")

        if not _is_utc_iso8601(processing_state.get("updated_at_utc")):
            errors.append(f"invalid:episodes[{idx}].processing_state.updated_at_utc:utc_iso8601")
        if not _is_utc_iso8601(processing_state.get("first_seen_at_utc")):
            errors.append(f"invalid:episodes[{idx}].processing_state.first_seen_at_utc:utc_iso8601")

        attempt_count = processing_state.get("attempt_count")
        if isinstance(attempt_count, bool) or not isinstance(attempt_count, int):
            errors.append(f"invalid:episodes[{idx}].processing_state.attempt_count:non_negative_int")
        elif attempt_count < 0:
            errors.append(f"invalid:episodes[{idx}].processing_state.attempt_count:non_negative_int")

        reason_code = processing_state.get("reason_code")
        if reason_code is not None and not isinstance(reason_code, str):
            errors.append(f"invalid:episodes[{idx}].processing_state.reason_code:string")

        last_error = processing_state.get("last_error")
        if last_error is not None and not isinstance(last_error, str):
            errors.append(f"invalid:episodes[{idx}].processing_state.last_error:string")

    return errors


def validate_payload(
    payload: dict[str, Any],
    *,
    contract_version: str | None = None,
) -> list[str]:
    target = contract_version or EXPECTED_CONTRACT_VERSION
    if target == CONTRACT_VERSION_V1:
        return _validate_payload_v1(payload)
    if target == CONTRACT_VERSION_V2:
        return validate_payload_v2(payload)
    return [f"unsupported_validation_target:{target}"]


def payload_fingerprint_sha256(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compatibility_policy() -> dict[str, Any]:
    return {
        "validator_version": VALIDATOR_VERSION,
        "compatibility_mode": "backward_compatible_reader_fail_closed_on_unknown_major",
        "latest_contract_version": EXPECTED_CONTRACT_VERSION,
        "supported_contract_versions": list(SUPPORTED_CONTRACT_VERSIONS),
        "supported_validation_targets": list(SUPPORTED_VALIDATION_TARGETS),
        "required_top_level_fields": list(REQUIRED_TOP_LEVEL_FIELDS),
        "required_episode_fields": list(REQUIRED_EPISODE_FIELDS),
        "v2_required_top_level_fields": list(V2_REQUIRED_TOP_LEVEL_FIELDS),
        "v2_required_episode_fields": list(V2_REQUIRED_EPISODE_FIELDS),
        "v2_required_utc_fields": [
            "generated_at_utc",
            "episodes[].published_at_utc",
            "episodes[].processing_state.updated_at_utc",
            "episodes[].processing_state.first_seen_at_utc",
        ],
        "v2_processing_state_status_enum": sorted(V2_ALLOWED_PROCESSING_STATES),
        "v2_gate_mode": "parallel_non_default",
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
