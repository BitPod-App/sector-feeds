#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CRITICAL_METRICS = (
    "spot_btc",
    "etf_net_flows",
    "derivatives_funding_oi_liquidations",
    "move_index",
    "dfii10",
    "dgs10",
    "broad_usd",
    "usdjpy",
    "rrp",
    "tga",
)

BUNDLE_VERSION = "weekly_critical_bundle.v1"
MISSING_MARKERS = {"", "n/a", "na", "none", "missing", "null"}


def _confidence_band(score: int) -> str:
    if score < 60:
        return "blocked"
    if score < 75:
        return "low"
    if score < 90:
        return "medium"
    return "high"


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _to_confidence(raw: str) -> int:
    text = _normalize_text(raw)
    if not text:
        return 0
    try:
        number = int(float(text))
    except ValueError:
        return 0
    return max(0, min(100, number))


def _is_truthy(raw: str) -> bool:
    return _normalize_text(raw).lower() in {"yes", "true", "1"}


def _is_missing_value(raw: str) -> bool:
    return _normalize_text(raw).lower() in MISSING_MARKERS


def _default_entry(metric: str) -> dict[str, Any]:
    return {
        "metric": metric,
        "value": "MISSING",
        "timestamp_utc": "N/A",
        "source_url": "N/A",
        "source_type": "none",
        "confidence_0_to_100": 0,
        "confidence_band": "blocked",
        "confidence_override_reason": "missing_metric_row",
        "scoring_usable": False,
    }


def parse_report_table(report_text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in report_text.splitlines():
        if "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        metric = parts[0]
        if metric not in CRITICAL_METRICS:
            continue
        rows[metric] = {
            "metric": metric,
            "value": parts[1],
            "timestamp_utc": parts[2],
            "source_url": parts[3],
            "source_type": parts[4],
            "confidence_0_to_100": _to_confidence(parts[5]),
            "confidence_override_reason": parts[6],
            "scoring_usable": _is_truthy(parts[7]),
        }
    return rows


def build_bundle(report_path: Path, as_of_utc: str, run_id: str) -> dict[str, Any]:
    rows = parse_report_table(report_path.read_text(encoding="utf-8"))
    metrics: list[dict[str, Any]] = []
    blocked_or_missing_count = 0

    for metric in CRITICAL_METRICS:
        entry = rows.get(metric, _default_entry(metric))
        confidence = int(entry["confidence_0_to_100"])
        value = str(entry["value"])
        scoring_usable = bool(entry["scoring_usable"])

        reasons: list[str] = []
        if _is_missing_value(value):
            reasons.append("missing_value")
        if confidence < 60:
            reasons.append("confidence_below_60")
        if not scoring_usable:
            reasons.append("scoring_not_usable")
        blocked = bool(reasons)
        if blocked:
            blocked_or_missing_count += 1

        metrics.append(
            {
                "metric": metric,
                "value": value,
                "timestamp_utc": str(entry["timestamp_utc"]),
                "source_url": str(entry["source_url"]),
                "source_type": str(entry["source_type"]),
                "confidence_0_to_100": confidence,
                "confidence_band": _confidence_band(confidence),
                "confidence_override_reason": str(entry["confidence_override_reason"]),
                "scoring_usable": scoring_usable,
                "blocked": blocked,
                "blocked_reasons": reasons,
            }
        )

    return {
        "contract_version": BUNDLE_VERSION,
        "run_id": run_id,
        "as_of_utc": as_of_utc,
        "source_report_path": str(report_path),
        "critical_metrics_total": len(CRITICAL_METRICS),
        "critical_metrics_missing_or_blocked_count": blocked_or_missing_count,
        "gate_status": "INCOMPLETE" if blocked_or_missing_count >= 2 else "COMPLETE",
        "metrics": metrics,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic weekly critical bundle from strict report artifact.")
    parser.add_argument("--report-md", required=True, help="Path to strict report markdown artifact.")
    parser.add_argument(
        "--output-json",
        default="artifacts/private/weekly_bundles/weekly_critical_bundle.json",
        help="Output bundle JSON path.",
    )
    parser.add_argument(
        "--as-of-utc",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        help="As-of timestamp (UTC ISO-8601).",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id. Defaults to weekly_bundle_<YYYYMMDDTHHMMSSZ>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_md).resolve()
    if not report_path.exists():
        raise SystemExit(f"Missing report file: {report_path}")

    run_id = args.run_id
    if not run_id:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"weekly_bundle_{stamp}"

    output_path = Path(args.output_json).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle(report_path=report_path, as_of_utc=args.as_of_utc, run_id=run_id)
    output_path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
