#!/usr/bin/env bash
set -euo pipefail

# Fails if tracked files exceed size constraints.
# Defaults:
# - hard max: 5 MiB for any tracked file
# - binary max: 2 MiB for common binary/media extensions

if ! command -v git >/dev/null 2>&1; then
  echo "Missing dependency: git"
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${repo_root}" ]]; then
  echo "Not inside a git repository."
  exit 1
fi

cd "${repo_root}"

hard_max_bytes="${REPO_FILE_HARD_MAX_BYTES:-5242880}"   # 5 MiB
binary_max_bytes="${REPO_FILE_BINARY_MAX_BYTES:-2097152}" # 2 MiB

binary_ext_regex='(mp3|mp4|mov|m4a|wav|flac|zip|tar|gz|7z|pdf|png|jpg|jpeg|webp|gif|ico|so|dylib|bin)$'

violations=0

while IFS= read -r -d '' path; do
  size="$(stat -f '%z' "${path}")"
  name_lc="$(printf '%s' "${path}" | tr '[:upper:]' '[:lower:]')"

  if [[ "${size}" -gt "${hard_max_bytes}" ]]; then
    echo "FAIL hard-max: ${path} (${size} bytes > ${hard_max_bytes})"
    violations=$((violations + 1))
    continue
  fi

  if [[ "${name_lc}" =~ \.${binary_ext_regex} ]] && [[ "${size}" -gt "${binary_max_bytes}" ]]; then
    echo "FAIL binary-max: ${path} (${size} bytes > ${binary_max_bytes})"
    violations=$((violations + 1))
  fi
done < <(git ls-files -z)

if [[ "${violations}" -gt 0 ]]; then
  echo "Repo size check failed with ${violations} violation(s)."
  exit 1
fi

echo "Repo size check passed."

