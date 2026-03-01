#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/init_proving_run.sh <RUN_ID> [--context <slug>] [--date <YYYY-MM-DD>]

Scaffolds docs/agents/runs/<RUN_ID>/ from proving-run templates.
Default behavior is no-overwrite: existing files are preserved.

Naming format (date-last):
  <artifact>_<context>_<YYYY-MM-DD>.md

Examples:
  bash scripts/init_proving_run.sh M9-PROVING-RUN-004
  bash scripts/init_proving_run.sh M9-PROVING-RUN-004 --context i24p31
USAGE
}

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 2
fi

RUN_ID="$1"
shift

if [ -z "$RUN_ID" ]; then
  usage >&2
  exit 2
fi

infer_default_context() {
  local run_id="$1"
  local uid
  uid="$(printf '%s' "$run_id" | cksum | awk '{print $1}' | cut -c1-6)"
  if printf '%s' "$run_id" | grep -Eq '.*-([0-9]{3,})$'; then
    printf 'run%s-u%s' "$(printf '%s' "$run_id" | sed -E 's/.*-([0-9]{3,})$/\1/')" "$uid"
  else
    printf 'run-u%s' "$uid"
  fi
}

CONTEXT="$(infer_default_context "$RUN_ID")"
DATE_UTC="$(date -u +"%Y-%m-%d")"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --context)
      CONTEXT="${2:-}"
      shift 2
      ;;
    --date)
      DATE_UTC="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "FATAL: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$CONTEXT" ] || [ -z "$DATE_UTC" ]; then
  echo "FATAL: context/date cannot be empty" >&2
  exit 2
fi

if ! printf '%s' "$DATE_UTC" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
  echo "FATAL: --date must be YYYY-MM-DD" >&2
  exit 2
fi

sanitize_slug() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

CONTEXT_SLUG="$(sanitize_slug "$CONTEXT")"
if [ -z "$CONTEXT_SLUG" ]; then
  echo "FATAL: context slug resolved empty after sanitization" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/docs/agents/proving-run/templates"
RUN_DIR="$REPO_ROOT/docs/agents/runs/$RUN_ID"
MANIFEST_PATH="$RUN_DIR/artifact_manifest.json"

REQUIRED_TEMPLATES=(
  "plan_template_v1.md"
  "execution_notes_template_v1.md"
  "verification_report_template_v1.md"
  "cj_gate_decision_template_v1.md"
  "result_template_v1.md"
  "retrospective_template_v1.md"
)

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "FATAL: template directory not found: $TEMPLATE_DIR" >&2
  exit 1
fi

validate_required_templates() {
  local missing=()
  local t
  for t in "${REQUIRED_TEMPLATES[@]}"; do
    if [ ! -f "$TEMPLATE_DIR/$t" ]; then
      missing+=("$TEMPLATE_DIR/$t")
    fi
  done

  if [ "${#missing[@]}" -gt 0 ]; then
    echo "FATAL: required proving-run templates missing:" >&2
    printf ' - %s\n' "${missing[@]}" >&2
    exit 1
  fi
}

validate_required_templates
mkdir -p "$RUN_DIR"

artifact_name() {
  local kind="$1"
  echo "${kind}_${CONTEXT_SLUG}_${DATE_UTC}.md"
}

PLAN_FILE="$(artifact_name plan)"
EXEC_FILE="$(artifact_name execution_notes)"
QA_FILE="$(artifact_name qa_report)"
DECISION_FILE="$(artifact_name final_decision)"
SUMMARY_FILE="$(artifact_name ticket_summary)"
RETRO_FILE="$(artifact_name retrospective)"

copy_if_missing() {
  local template_name="$1"
  local dst="$2"
  local src="$TEMPLATE_DIR/$template_name"

  if [ -e "$dst" ]; then
    echo "SKIP existing: ${dst#$REPO_ROOT/}"
  else
    cp "$src" "$dst"
    echo "CREATE: ${dst#$REPO_ROOT/}"
  fi
}

copy_if_missing "plan_template_v1.md" "$RUN_DIR/$PLAN_FILE"
copy_if_missing "execution_notes_template_v1.md" "$RUN_DIR/$EXEC_FILE"
copy_if_missing "verification_report_template_v1.md" "$RUN_DIR/$QA_FILE"
copy_if_missing "cj_gate_decision_template_v1.md" "$RUN_DIR/$DECISION_FILE"
copy_if_missing "result_template_v1.md" "$RUN_DIR/$SUMMARY_FILE"
copy_if_missing "retrospective_template_v1.md" "$RUN_DIR/$RETRO_FILE"

cat > "$MANIFEST_PATH" <<MANIFEST
{
  "run_id": "$RUN_ID",
  "context": "$CONTEXT_SLUG",
  "date_utc": "$DATE_UTC",
  "artifacts": {
    "plan": "$PLAN_FILE",
    "execution_notes": "$EXEC_FILE",
    "qa_report": "$QA_FILE",
    "final_decision": "$DECISION_FILE",
    "ticket_summary": "$SUMMARY_FILE",
    "retrospective": "$RETRO_FILE"
  }
}
MANIFEST

echo "proving_run_init=OK run_id=$RUN_ID path=${RUN_DIR#$REPO_ROOT/} manifest=${MANIFEST_PATH#$REPO_ROOT/}"
