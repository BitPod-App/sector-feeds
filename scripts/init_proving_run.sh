#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: bash scripts/init_proving_run.sh <RUN_ID>

Scaffolds docs/agents/runs/<RUN_ID>/ from proving-run templates.
Default behavior is no-overwrite: existing files are preserved.
USAGE
}

if [ "$#" -ne 1 ]; then
  usage >&2
  exit 2
fi

RUN_ID="$1"
if [ -z "$RUN_ID" ]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE_DIR="$REPO_ROOT/docs/agents/proving-run/templates"
RUN_DIR="$REPO_ROOT/docs/agents/runs/$RUN_ID"
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

copy_if_missing "plan_template_v1.md" "$RUN_DIR/plan.md"
copy_if_missing "execution_notes_template_v1.md" "$RUN_DIR/execution_notes.md"
copy_if_missing "verification_report_template_v1.md" "$RUN_DIR/verification_report.md"
copy_if_missing "cj_gate_decision_template_v1.md" "$RUN_DIR/cj_gate_decision.md"
copy_if_missing "result_template_v1.md" "$RUN_DIR/result.md"
copy_if_missing "retrospective_template_v1.md" "$RUN_DIR/retrospective.md"

echo "proving_run_init=OK run_id=$RUN_ID path=${RUN_DIR#$REPO_ROOT/}"
