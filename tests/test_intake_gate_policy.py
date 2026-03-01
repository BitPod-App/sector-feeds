from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bitpod.intake_gate_policy import close_ready, evaluate_drift, guardrail, load_policy, validate_status_contract


class IntakeGatePolicyTests(unittest.TestCase):
    def test_load_policy_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m5_policy.json"
            path.write_text(
                """{
  "policy_version": "m5_intake_ops_policy.v1",
  "milestone": "M-5",
  "required_validation_target": "bitregime_core_intake.v2",
  "rollback_guardrail_consecutive_failures": 2,
  "close_ready_consecutive_greens": 3,
  "freeze_action_on_guardrail": "freeze_intake_contract_changes_and_route_to_incident_triage"
}
""",
                encoding="utf-8",
            )
            policy = load_policy(path)
            self.assertEqual(policy["milestone"], "M-5")
            self.assertEqual(policy["required_validation_target"], "bitregime_core_intake.v2")

    def test_guardrail_and_close_ready(self) -> None:
        policy = {
            "policy_version": "m5_intake_ops_policy.v1",
            "milestone": "M-5",
            "required_validation_target": "bitregime_core_intake.v2",
            "rollback_guardrail_consecutive_failures": 2,
            "close_ready_consecutive_greens": 3,
            "freeze_action_on_guardrail": "freeze_intake_contract_changes_and_route_to_incident_triage",
        }
        self.assertFalse(close_ready(2, policy))
        self.assertTrue(close_ready(3, policy))
        self.assertEqual(guardrail(1, policy), (False, "none"))
        self.assertEqual(
            guardrail(2, policy),
            (True, "freeze_intake_contract_changes_and_route_to_incident_triage"),
        )

    def test_status_contract_and_drift(self) -> None:
        policy = {
            "policy_version": "m5_intake_ops_policy.v1",
            "milestone": "M-5",
            "required_validation_target": "bitregime_core_intake.v2",
            "rollback_guardrail_consecutive_failures": 2,
            "close_ready_consecutive_greens": 3,
            "freeze_action_on_guardrail": "freeze_intake_contract_changes_and_route_to_incident_triage",
        }
        record = {
            "status_schema_version": "intake_gate_daily_status.v2",
            "contract_ok": True,
            "failure_reason_categories": [],
            "consecutive_failures": 0,
            "consecutive_greens": 4,
            "m5_close_ready_3_consecutive_greens": True,
            "rollback_guardrail_triggered": False,
            "escalation": "none",
            "required_validation_target": "bitregime_core_intake.v2",
            "gate_green": True,
            "rollback_guardrail_threshold": 2,
            "close_ready_required_consecutive_greens": 3,
        }
        self.assertEqual(validate_status_contract(record), [])
        drift = evaluate_drift(policy, record)
        self.assertTrue(drift["drift_ok"])
        record["required_validation_target"] = "bitregime_core_intake.v1"
        drift = evaluate_drift(policy, record)
        self.assertFalse(drift["drift_ok"])


if __name__ == "__main__":
    unittest.main()
