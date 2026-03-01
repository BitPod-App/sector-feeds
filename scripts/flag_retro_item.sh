#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/flag_retro_item.sh --note "<text>" [--scope "<scope>"] [--source "<source>"] [--run-id "<run-id>"]

Purpose:
  Append a retrospective input item to the coordination inbox for later meeting review.

Defaults:
  scope=general
  source=manual
USAGE
}

note=""
scope="general"
source="manual"
run_id=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --note)
      note="${2:-}"
      shift 2
      ;;
    --scope)
      scope="${2:-}"
      shift 2
      ;;
    --source)
      source="${2:-}"
      shift 2
      ;;
    --run-id)
      run_id="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [ -z "$note" ]; then
        note="$1"
        shift
      else
        echo "FATAL: unknown argument: $1" >&2
        usage >&2
        exit 2
      fi
      ;;
  esac
done

if [ -z "$note" ]; then
  echo "FATAL: --note is required" >&2
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COORD_DIR="$REPO_ROOT/artifacts/coordination"
QUEUE_JSONL="$COORD_DIR/retrospective_flag_queue.jsonl"
QUEUE_MD="$COORD_DIR/retrospective_flag_queue.md"

mkdir -p "$COORD_DIR"

ts_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
ts_compact="$(date -u +"%Y%m%dT%H%M%SZ")"
flag_id="retro-$ts_compact-$$"

escape_json() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  printf '%s' "$s"
}

md_cell() {
  local s="$1"
  s="${s//$'\n'/ }"
  s="${s//|/\\|}"
  printf '%s' "$s"
}

note_json="$(escape_json "$note")"
scope_json="$(escape_json "$scope")"
source_json="$(escape_json "$source")"
run_id_json="$(escape_json "$run_id")"

printf '{"id":"%s","created_at_utc":"%s","status":"open","scope":"%s","source":"%s","run_id":"%s","note":"%s"}\n' \
  "$flag_id" "$ts_iso" "$scope_json" "$source_json" "$run_id_json" "$note_json" >> "$QUEUE_JSONL"

if [ ! -f "$QUEUE_MD" ]; then
  cat > "$QUEUE_MD" <<'MDHEADER'
# Retrospective Flag Queue

Use this queue to capture retrospective input items during execution. These are inputs for a later retrospective meeting, not full retrospectives.

| created_at_utc | id | status | scope | source | run_id | note |
| --- | --- | --- | --- | --- | --- | --- |
MDHEADER
fi

printf '| %s | %s | open | %s | %s | %s | %s |\n' \
  "$ts_iso" \
  "$flag_id" \
  "$(md_cell "$scope")" \
  "$(md_cell "$source")" \
  "$(md_cell "$run_id")" \
  "$(md_cell "$note")" >> "$QUEUE_MD"

echo "retro_flag=OK id=$flag_id jsonl=${QUEUE_JSONL#$REPO_ROOT/} md=${QUEUE_MD#$REPO_ROOT/}"
