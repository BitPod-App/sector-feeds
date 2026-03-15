#!/usr/bin/env bash

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "Missing dependency: rg (ripgrep). Install with: brew install ripgrep"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_root="${HOME}/.agents/skills/taylor"
skill_file="${skill_root}/SKILL.md"
app_mission_file="${skill_root}/references/app-mission-vision.md"
agent_contract_file="${skill_root}/references/taylor-agent-contract.md"
report_template_file="${skill_root}/references/report-template.md"
bridge_sessions_file="${skill_root}/references/bridge-gpt-team-sessions.md"

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

if ! rg -q 'references/report-template\.md' "${skill_file}"; then
  echo "Missing reference to report-template.md in ${skill_file}"
  exit 1
fi

if ! rg -i -e 'periodic.*ad hoc|ad hoc.*periodic' -q "${skill_file}"; then
  echo "Missing periodic + ad hoc cadence framing in ${skill_file}"
  exit 1
fi

if ! rg -q 'references/bridge-gpt-team-sessions\.md' "${skill_file}"; then
  echo "Missing reference to bridge-gpt-team-sessions.md in ${skill_file}"
  exit 1
fi

if ! rg -q '^## North Star \(invariant\)$' "${app_mission_file}"; then
  echo "Missing '## North Star (invariant)' section in ${app_mission_file}"
  exit 1
fi

echo "Taylor skill check passed."
