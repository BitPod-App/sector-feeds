#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <show_key> [min_caption_words] [min_episode_age_minutes]"
  exit 2
fi

SHOW_KEY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load optional runtime secrets/config once (kept outside committed defaults).
if [ -f "$REPO_ROOT/.bitpod_runtime.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_runtime.env"
elif [ -f "$REPO_ROOT/scripts/bitpod_runtime.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/scripts/bitpod_runtime.env"
fi

# Load optional budget/runtime defaults once so users do not need to pass env vars every run.
if [ -f "$REPO_ROOT/.bitpod_budget.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_budget.env"
elif [ -f "$REPO_ROOT/scripts/bitpod_budget.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/scripts/bitpod_budget.env"
fi

MIN_CAPTION_WORDS="${2:-${MIN_CAPTION_WORDS:-120}}"
MIN_EPISODE_AGE_MINUTES="${3:-${MIN_EPISODE_AGE_MINUTES:-180}}"
WEEKLY_GPT_REPORT="${WEEKLY_GPT_REPORT:-0}"
TOOLS_COST_CTL="/Users/cjarguello/bitpod-app/tools/costs/cost_ctl.py"

run_cost_guard() {
  if [ ! -x "$TOOLS_COST_CTL" ]; then
    return 0
  fi
  local args=()
  if [ -n "${COST_SOURCE:-}" ]; then args+=(--source "$COST_SOURCE"); fi
  if [ -n "${COST_WINDOW_HOURS:-}" ]; then args+=(--window-hours "$COST_WINDOW_HOURS"); fi
  if [ -n "${COST_RUN_WARN:-}" ]; then args+=(--run-warn "$COST_RUN_WARN"); fi
  if [ -n "${COST_RUN_FAIL:-}" ]; then args+=(--run-fail "$COST_RUN_FAIL"); fi
  if [ -n "${COST_DAILY_WARN:-}" ]; then args+=(--daily-warn "$COST_DAILY_WARN"); fi
  if [ -n "${COST_DAILY_FAIL:-}" ]; then args+=(--daily-fail "$COST_DAILY_FAIL"); fi
  if [ "${COST_WARN_EXIT_0:-0}" = "1" ]; then args+=(--warn-exit-0); fi
  python3 "$TOOLS_COST_CTL" "${args[@]}"
}

cd "$REPO_ROOT"
run_cost_guard
.venv311/bin/python -m bitpod discover --show "$SHOW_KEY"
.venv311/bin/python -m bitpod sync \
  --show "$SHOW_KEY" \
  --max-episodes 1 \
  --source-policy balanced \
  --min-caption-words "$MIN_CAPTION_WORDS" \
  --min-episode-age-minutes "$MIN_EPISODE_AGE_MINUTES"

.venv311/bin/python - "$SHOW_KEY" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

show_key = sys.argv[1]
repo_root = Path(sys.argv[2])
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
status_name = Path(stable_pointer).stem + "_status.json"
status_path = repo_root / "transcripts" / show_key / status_name
if not status_path.exists():
    print(f"ERROR: missing status artifact: {status_path}")
    raise SystemExit(2)

payload = json.loads(status_path.read_text(encoding="utf-8"))
run_status = payload.get("run_status")
included = bool(payload.get("included_in_pointer"))
if run_status == "ok" and included:
    print(f"Weekly run OK for {show_key}: latest episode included in pointer")
    raise SystemExit(0)

print(f"Weekly run FAILED for {show_key} or latest not included in pointer")
print(f"run_status={run_status} included_in_pointer={included}")
print(f"failure_stage={payload.get('failure_stage')} reason={payload.get('failure_reason')}")
raise SystemExit(1)
PY

if [ "$WEEKLY_GPT_REPORT" = "1" ]; then
  TRANSCRIPT_PATH="$(python3 - "$SHOW_KEY" "$REPO_ROOT" <<'PY'
import json
import sys
from pathlib import Path

show_key = sys.argv[1]
repo_root = Path(sys.argv[2])
shows = json.loads((repo_root / "shows.json").read_text(encoding="utf-8"))
show = shows.get("shows", {}).get(show_key, {})
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
print(str(repo_root / "transcripts" / show_key / stable_pointer))
PY
)"
  REPORT_NAME="gpt-bitreport-pods-all-$(date -u +%Y%m%d-%H%M).md"
  .venv311/bin/python scripts/gpt_report_from_transcript.py \
    --transcript-path "$TRANSCRIPT_PATH" \
    --report-name "$REPORT_NAME" \
    --show-key "$SHOW_KEY"
  run_cost_guard
fi
