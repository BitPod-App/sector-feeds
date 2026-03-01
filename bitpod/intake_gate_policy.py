from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def milestone_close_ready_key(milestone: str, required_consecutive_greens: int) -> str:
    normalized = "".join(ch.lower() for ch in milestone if ch.isalnum())
    if not normalized:
        normalized = "milestone"
    return f"{normalized}_close_ready_{int(required_consecutive_greens)}_consecutive_greens"


def load_policy(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_policy_json:{path}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"invalid_policy_shape:{path}")
    required = (
        "policy_version",
        "milestone",
        "required_validation_target",
        "rollback_guardrail_consecutive_failures",
        "close_ready_consecutive_greens",
        "freeze_action_on_guardrail",
    )
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"missing_policy_keys:{','.join(sorted(missing))}")
    owner = raw.get("owner_oncall")
    if owner is not None and (not isinstance(owner, str) or not owner.strip()):
        raise ValueError("invalid_policy_owner_oncall")
    milestone_status = raw.get("milestone_status")
    if milestone_status is not None:
        allowed_statuses = {"PLANNED", "IN_PROGRESS", "DONE"}
        if not isinstance(milestone_status, str) or milestone_status not in allowed_statuses:
            raise ValueError("invalid_policy_milestone_status")
    if not isinstance(raw["required_validation_target"], str) or not raw["required_validation_target"].strip():
        raise ValueError("invalid_policy_required_validation_target")
    if not isinstance(raw["freeze_action_on_guardrail"], str) or not raw["freeze_action_on_guardrail"].strip():
        raise ValueError("invalid_policy_freeze_action_on_guardrail")
    for key in ("rollback_guardrail_consecutive_failures", "close_ready_consecutive_greens"):
        val = raw.get(key)
        if isinstance(val, bool) or not isinstance(val, int) or val < 1:
            raise ValueError(f"invalid_policy_{key}")
    return raw


def close_ready(consecutive_greens: int, policy: dict[str, Any]) -> bool:
    required = int(policy["close_ready_consecutive_greens"])
    return consecutive_greens >= required


def guardrail(consecutive_failures: int, policy: dict[str, Any]) -> tuple[bool, str]:
    threshold = int(policy["rollback_guardrail_consecutive_failures"])
    triggered = consecutive_failures >= threshold
    escalation = str(policy["freeze_action_on_guardrail"]) if triggered else "none"
    return triggered, escalation


def validate_status_contract(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = (
        "status_schema_version",
        "contract_ok",
        "failure_reason_categories",
        "consecutive_failures",
        "consecutive_greens",
        "milestone_close_ready",
        "rollback_guardrail_triggered",
        "escalation",
        "required_validation_target",
        "gate_green",
    )
    for key in required_keys:
        if key not in record:
            errors.append(f"missing_status_key:{key}")
    bool_keys = (
        "contract_ok",
        "gate_green",
        "milestone_close_ready",
        "rollback_guardrail_triggered",
    )
    for key in bool_keys:
        if key in record and not isinstance(record[key], bool):
            errors.append(f"invalid_status_type:{key}:bool")
    int_keys = ("consecutive_failures", "consecutive_greens")
    for key in int_keys:
        if key in record and (isinstance(record[key], bool) or not isinstance(record[key], int) or record[key] < 0):
            errors.append(f"invalid_status_type:{key}:non_negative_int")
    if "failure_reason_categories" in record and not isinstance(record.get("failure_reason_categories"), list):
        errors.append("invalid_status_type:failure_reason_categories:list")
    return errors


def evaluate_drift(policy: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    checks = []

    def add_check(name: str, expected: Any, observed: Any) -> None:
        checks.append({"name": name, "expected": expected, "observed": observed, "ok": expected == observed})

    add_check("required_validation_target", policy["required_validation_target"], record.get("required_validation_target"))
    add_check(
        "rollback_guardrail_consecutive_failures",
        int(policy["rollback_guardrail_consecutive_failures"]),
        int(record.get("rollback_guardrail_threshold", -1)),
    )
    add_check(
        "close_ready_consecutive_greens",
        int(policy["close_ready_consecutive_greens"]),
        int(record.get("close_ready_required_consecutive_greens", -1)),
    )
    expected_escalation = (
        str(policy["freeze_action_on_guardrail"])
        if bool(record.get("rollback_guardrail_triggered"))
        else "none"
    )
    add_check("guardrail_escalation_value", expected_escalation, record.get("escalation"))

    return {
        "drift_ok": all(bool(c["ok"]) for c in checks),
        "checks": checks,
    }
