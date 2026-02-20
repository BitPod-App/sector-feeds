#!/usr/bin/env bash

set -euo pipefail

skill_root="${HOME}/.agents/skills/taylor"
skill_file="${skill_root}/SKILL.md"
reference_file="${skill_root}/references/app-mission-vision.md"

if [[ ! -f "${skill_file}" ]]; then
  echo "Missing file: ${skill_file}"
  exit 1
fi

if [[ ! -f "${reference_file}" ]]; then
  echo "Missing file: ${reference_file}"
  exit 1
fi

if ! rg -q '^name:\s*taylor$' "${skill_file}"; then
  echo "Expected 'name: taylor' in ${skill_file}"
  exit 1
fi

if ! rg -q '^## Project vision & architecture knowledge$' "${skill_file}"; then
  echo "Missing required section header in ${skill_file}"
  exit 1
fi

if ! rg -q '^## North Star \(invariant\)$' "${reference_file}"; then
  echo "Missing '## North Star (invariant)' section in ${reference_file}"
  exit 1
fi

echo "Taylor skill check passed."
