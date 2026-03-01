from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def evaluate_intake_readiness(status_payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    latest_raw = status_payload.get("public_permalink_latest_path")
    status_raw = status_payload.get("public_permalink_status_path")
    intake_raw = status_payload.get("public_permalink_intake_path")
    discovery_raw = status_payload.get("public_permalink_discovery_path")

    required_path_values = {
        "public_permalink_latest_path": latest_raw,
        "public_permalink_status_path": status_raw,
        "public_permalink_intake_path": intake_raw,
        "public_permalink_discovery_path": discovery_raw,
    }

    required_paths: dict[str, Path] = {}
    for key, value in required_path_values.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(f"missing:{key}")
            continue
        p = Path(value)
        required_paths[key] = p
        if not p.exists():
            errors.append(f"missing_file:{key}:{p}")

    status_json = _read_json(required_paths["public_permalink_status_path"]) if "public_permalink_status_path" in required_paths else None
    if status_json is None:
        errors.append("invalid_json:public_permalink_status_path")
    else:
        if status_json.get("contract_version") != "public_permalink_status.v1":
            errors.append("unexpected_contract:public_permalink_status")
        if status_json.get("latest_path") != "latest.md":
            errors.append("unexpected_latest_path")
        if status_json.get("transcript_path") != "transcript.md":
            errors.append("unexpected_transcript_path")
        if status_json.get("intake_path") != "intake.md":
            errors.append("unexpected_intake_path")
        if status_json.get("discovery_path") != "discovery.json":
            errors.append("unexpected_discovery_path")

    discovery_json = _read_json(required_paths["public_permalink_discovery_path"]) if "public_permalink_discovery_path" in required_paths else None
    if discovery_json is None:
        errors.append("invalid_json:public_permalink_discovery_path")
    else:
        if discovery_json.get("contract_version") != "public_permalink_discovery.v1":
            errors.append("unexpected_contract:public_permalink_discovery")
        entrypoints = discovery_json.get("entrypoints")
        if not isinstance(entrypoints, dict):
            errors.append("missing:discovery_entrypoints")
        else:
            if entrypoints.get("intake_md") != "intake.md":
                errors.append("unexpected_discovery_entrypoint:intake_md")
            if entrypoints.get("transcript_md") != "transcript.md":
                errors.append("unexpected_discovery_entrypoint:transcript_md")
            if entrypoints.get("latest_md") != "latest.md":
                errors.append("unexpected_discovery_entrypoint:latest_md")
            if entrypoints.get("status_json") != "status.json":
                errors.append("unexpected_discovery_entrypoint:status_json")
            if entrypoints.get("episodes_dir") != "episodes/":
                errors.append("unexpected_discovery_entrypoint:episodes_dir")

    if "public_permalink_latest_path" in required_paths:
        latest_text = required_paths["public_permalink_latest_path"].read_text(encoding="utf-8", errors="ignore")
        if "# Transcript Index" not in latest_text:
            errors.append("missing_marker:latest:# Transcript Index")
        if "Processed Episodes (oldest to newest)" not in latest_text:
            errors.append("missing_marker:latest:Processed Episodes (oldest to newest)")

    if "public_permalink_intake_path" in required_paths:
        intake_text = required_paths["public_permalink_intake_path"].read_text(encoding="utf-8", errors="ignore")
        if "# Transcript Intake" not in intake_text:
            errors.append("missing_marker:intake:# Transcript Intake")
        for marker in ("[latest.md](latest.md)", "[status.json](status.json)", "[discovery.json](discovery.json)"):
            if marker not in intake_text:
                errors.append(f"missing_marker:intake:{marker}")
        if "[transcript.md](transcript.md)" not in intake_text:
            errors.append("missing_marker:intake:[transcript.md](transcript.md)")

    return {"ok": not errors, "errors": errors}
