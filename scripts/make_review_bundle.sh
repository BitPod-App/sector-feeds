#!/usr/bin/env bash

set -euo pipefail

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

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to generate review bundle: working tree is dirty. Commit or stash changes first."
  exit 1
fi

head_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${head_branch}" == "HEAD" ]]; then
  echo "Refusing to generate review bundle from detached HEAD."
  exit 1
fi

base_branch=""
for candidate in main master; do
  if git fetch --quiet origin "${candidate}"; then
    base_branch="${candidate}"
    break
  fi
done

if [[ -z "${base_branch}" ]]; then
  echo "Unable to detect/fetch base branch from origin (tried: main, master)."
  exit 1
fi

base_ref="origin/${base_branch}"
if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
  echo "Base ref is not a valid commit: ${base_ref}"
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
safe_branch="${head_branch//\//_}"
out_dir="${repo_root}/artifacts/review_bundles"
out_file="${out_dir}/${safe_branch}_${timestamp}.md"
mkdir -p "${out_dir}"

head_sha="$(git rev-parse HEAD)"
base_sha="$(git rev-parse "${base_ref}")"

{
  echo "# Review Bundle"
  echo
  echo "## A) Context"
  echo "- Repo: \
\`${repo_root}\`"
  echo "- Base Branch: \
\`${base_ref}\`"
  echo "- Head Branch: \
\`${head_branch}\`"
  echo "- Base Commit: \
\`${base_sha}\`"
  echo "- Head Commit: \
\`${head_sha}\`"
  echo "- Timestamp (UTC): \
\`${timestamp}\`"
  echo "- Generation Command: \
\`bash scripts/make_review_bundle.sh\`"
  echo
  echo "### Commits (\`${base_ref}..HEAD\`)"
  echo '```text'
  git rev-list --oneline "${base_ref}..HEAD"
  echo '```'
  echo
  echo "## B) git diff --stat (\`${base_ref}...HEAD\`)"
  echo '```text'
  git diff --stat "${base_ref}...HEAD"
  echo '```'
  echo
  echo "## C) full git diff (\`${base_ref}...HEAD\`)"
  echo '```diff'
  git diff "${base_ref}...HEAD"
  echo '```'
  echo
  echo "## D) verification outputs"

  ran_any=0
  if [[ -x "${repo_root}/scripts/check_taylor_skill.sh" ]]; then
    ran_any=1
    echo
    echo "### Command"
    echo '```bash'
    echo "bash scripts/check_taylor_skill.sh"
    echo '```'
    echo "### Output"
    echo '```text'
    bash "${repo_root}/scripts/check_taylor_skill.sh"
    echo '```'
  fi

  if [[ -x "${repo_root}/scripts/check_taylor_agent.sh" ]]; then
    ran_any=1
    echo
    echo "### Command"
    echo '```bash'
    echo "bash scripts/check_taylor_agent.sh"
    echo '```'
    echo "### Output"
    echo '```text'
    bash "${repo_root}/scripts/check_taylor_agent.sh"
    echo '```'
  fi

  if [[ ${ran_any} -eq 0 ]]; then
    echo "No verification commands configured."
  fi

  echo
  echo "## E) decisions needed"
  echo "- None."
} > "${out_file}"

bundle_sha256="$(python3 - <<'PY' "${out_file}"
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
h = hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda: f.read(65536), b''):
        h.update(chunk)
print(h.hexdigest())
PY
)"

echo "Bundle created: ${out_file}"
echo "BUNDLE_SHA256: ${bundle_sha256}"
echo "Generation command: bash scripts/make_review_bundle.sh"
