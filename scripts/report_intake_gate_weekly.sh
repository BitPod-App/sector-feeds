#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/report_intake_gate_weekly.sh [log_jsonl_path] [output_md_path]

Reads daily gate log JSONL, summarizes the most recent 7 records,
and writes a weekly Markdown report.
USAGE
}

if [ "$#" -gt 2 ]; then
  usage
  exit 2
fi

LOG_JSONL="${1:-artifacts/coordination/intake_gate_daily_log.jsonl}"
OUT_MD="${2:-artifacts/coordination/intake_gate_weekly_summary.md}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 - "$LOG_JSONL" "$OUT_MD" <<'PY'
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

log_path = Path(sys.argv[1])
out_md = Path(sys.argv[2])
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

rows: list[dict] = []
if log_path.exists():
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)

recent = rows[-7:]
count = len(recent)
v2_green = sum(1 for r in recent if bool(r.get("v2_contract_ok") if "v2_contract_ok" in r else r.get("v2_target_contract_ok")))
all_green = sum(1 for r in recent if bool(r.get("gate_green") if "gate_green" in r else r.get("all_green")))
close_ready_days = sum(1 for r in recent if bool(r.get("m5_close_ready_3_consecutive_greens")))
guardrail_hits = sum(1 for r in recent if bool(r.get("rollback_guardrail_triggered")))

failure_category_counts: dict[str, int] = {}
for row in recent:
    cats = row.get("failure_reason_categories")
    if not isinstance(cats, list):
        continue
    for cat in cats:
        text = str(cat).strip()
        if not text:
            continue
        failure_category_counts[text] = failure_category_counts.get(text, 0) + 1

def pct(ok: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{(ok / total) * 100:.1f}%"

lines = [
    "# Intake Gate Weekly Summary",
    "",
    f"- generated_at_utc: `{now}`",
    f"- log_path: `{log_path.resolve()}`",
    f"- records_considered: `{count}`",
    "",
    "## Pass Rates (last up to 7 records)",
    f"- v2_contract_ok: `{v2_green}/{count}` ({pct(v2_green, count)})",
    f"- gate_green: `{all_green}/{count}` ({pct(all_green, count)})",
    f"- rollback_guardrail_triggered_days: `{guardrail_hits}/{count}`",
    f"- m5_close_ready_3_consecutive_greens_days: `{close_ready_days}/{count}`",
    "",
    "## Failure Categories (rows where present)",
]

if not failure_category_counts:
    lines.append("- none")
else:
    for cat, cat_count in sorted(failure_category_counts.items()):
        lines.append(f"- {cat}: `{cat_count}`")

lines.extend([
    "",
    "## Daily Rows",
])

if not recent:
    lines.append("- none")
else:
    for r in recent:
        gate_green = bool(r.get("gate_green") if "gate_green" in r else r.get("all_green"))
        v2_ok = bool(r.get("v2_contract_ok") if "v2_contract_ok" in r else r.get("v2_target_contract_ok"))
        lines.append(
            "- "
            + f"date_utc=`{r.get('date_utc')}` "
            + f"v2_contract_ok=`{v2_ok}` "
            + f"gate_green=`{gate_green}` "
            + f"consecutive_failures=`{r.get('consecutive_failures')}` "
            + f"guardrail=`{bool(r.get('rollback_guardrail_triggered'))}`"
        )

out_md.parent.mkdir(parents=True, exist_ok=True)
out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"output_path": str(out_md.resolve()), "records_considered": count}, indent=2))
PY
