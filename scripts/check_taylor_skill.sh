#!/usr/bin/env bash

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "Missing dependency: rg (ripgrep). Install with: brew install ripgrep"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT_PREREQ="${BITPOD_TAYLOR_PREREQ_STRICT:-0}"

is_truthy() {
  case "${1:-0}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

skip_or_fail() {
  local msg="$1"
  if is_truthy "${STRICT_PREREQ}"; then
    echo "FAIL: ${msg}"
    exit 1
  fi
  echo "SKIP: ${msg}"
  echo "Set BITPOD_TAYLOR_PREREQ_STRICT=1 to enforce hard-fail behavior."
  exit 0
}

skill_candidates=()
if [[ -n "${TAYLOR_SKILL_ROOT:-}" ]]; then
  skill_candidates+=("${TAYLOR_SKILL_ROOT}")
else
  skill_candidates+=(
    "${HOME}/.agents/skills/taylor"
    "${repo_root}/../.codex/skills/taylor"
    "${HOME}/.codex/skills/taylor"
  )
fi

skill_root=""
for candidate in "${skill_candidates[@]}"; do
  if [[ -f "${candidate}/SKILL.md" ]]; then
    skill_root="${candidate}"
    break
  fi
done

if [[ -z "${skill_root}" ]]; then
  skip_or_fail "Taylor canonical skill not found. Checked: ${skill_candidates[*]}. Override with TAYLOR_SKILL_ROOT=/path/to/taylor"
fi

skill_file="${skill_root}/SKILL.md"
app_mission_file="${skill_root}/references/app-mission-vision.md"
agent_contract_file="${skill_root}/references/taylor-agent-contract.md"
report_template_file="${skill_root}/references/report-template.md"
bridge_sessions_file="${skill_root}/references/bridge-gpt-team-sessions.md"
runtime_policy_file=""
runtime_policy_candidates=(
  "${repo_root}/../tools/taylor/policy/taylor_policy.yaml"
  "${repo_root}/../bitpod-tools/tools/taylor/policy/taylor_policy.yaml"
)
for p in "${runtime_policy_candidates[@]}"; do
  if [[ -f "${p}" ]]; then
    runtime_policy_file="${p}"
    break
  fi
done

required_files=(
  "${skill_file}"
  "${app_mission_file}"
  "${agent_contract_file}"
  "${report_template_file}"
  "${bridge_sessions_file}"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "${f}" ]]; then
    echo "Missing file: ${f}"
    exit 1
  fi
done
echo "OK: Required canonical files present (${skill_root})"

if ! rg -q '^name:\s*taylor$' "${skill_file}"; then
  echo "Expected 'name: taylor' in ${skill_file}"
  exit 1
fi

if ! rg -q '^## Project vision & architecture knowledge$' "${skill_file}"; then
  echo "Missing required section header in ${skill_file}"
  exit 1
fi

if ! rg -q 'references/report-template\.md' "${skill_file}" && \
   ! { [[ -n "${runtime_policy_file}" ]] && rg -q 'report-template\.md' "${runtime_policy_file}"; }; then
  echo "Missing reference to report-template.md in SKILL.md or runtime policy"
  exit 1
fi

if ! rg -i -e 'periodic.*ad hoc|ad hoc.*periodic' -q "${skill_file}" && \
   ! { [[ -n "${runtime_policy_file}" ]] && rg -i -e 'periodic.*ad hoc|ad hoc.*periodic' -q "${runtime_policy_file}"; }; then
  echo "Missing periodic + ad hoc cadence framing in SKILL.md or runtime policy"
  exit 1
fi

if ! rg -q 'references/bridge-gpt-team-sessions\.md' "${skill_file}" && \
   ! { [[ -n "${runtime_policy_file}" ]] && rg -q 'bridge-gpt-team-sessions\.md' "${runtime_policy_file}"; }; then
  echo "Missing reference to bridge-gpt-team-sessions.md in SKILL.md or runtime policy"
  exit 1
fi

if ! rg -q '^## North Star \(invariant\)$' "${app_mission_file}"; then
  echo "Missing '## North Star (invariant)' section in ${app_mission_file}"
  exit 1
fi

if [[ -n "${runtime_policy_file}" ]]; then
  echo "OK: Runtime policy detected (optional): ${runtime_policy_file}"
  if ! rg -q '\.agents/skills/taylor|~/.agents/skills/taylor|\$\{HOME\}/\.agents/skills/taylor|/\.agents/skills/taylor' "${runtime_policy_file}"; then
    echo "Runtime policy exists but does not reference canonical external skill path: ${runtime_policy_file}"
    exit 1
  fi
fi

echo "Taylor skill check passed."
