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
changed_files="$(git diff --name-only "${base_ref}...HEAD")"

critical_regex='(^|/)(scoring|score|verification|verify|schema|schemas|manifest|determinism|model|policy|weights|events)(/|_|\.|$)'
critical_touched=0
if [[ -n "${changed_files}" ]] && echo "${changed_files}" | rg -q -i "${critical_regex}"; then
  critical_touched=1
fi

if [[ "${critical_touched}" -eq 0 ]]; then
  echo "No critical surfaces touched; local QA artifact gate not required."
  exit 0
fi

commit_sha="$(git rev-parse HEAD)"
qa_dir="${repo_root}/artifacts/taylor_qa/${commit_sha}"
qa_review="${qa_dir}/qa_review.md"
manifest="${qa_dir}/qa_run_manifest.json"

if [[ ! -f "${qa_review}" ]]; then
  echo "Missing required local QA artifact: ${qa_review}"
  exit 1
fi

if [[ ! -f "${manifest}" ]]; then
  echo "Missing required local QA manifest: ${manifest}"
  exit 1
fi

python3 - <<'PY' "${manifest}" "${commit_sha}"
import hashlib
import json
import pathlib
import sys

manifest_path = pathlib.Path(sys.argv[1])
expected_commit = sys.argv[2]

m = json.loads(manifest_path.read_text(encoding="utf-8"))
errors = []

if m.get("mode") != "LOCAL":
    errors.append(f"mode must be LOCAL, got: {m.get('mode')}")
if m.get("commit_sha") != expected_commit:
    errors.append(f"commit_sha mismatch: {m.get('commit_sha')} != {expected_commit}")
if m.get("footer_compliant") is not False:
    errors.append("footer_compliant must be false for LOCAL mode")
if m.get("footer_synthetic") is not False:
    errors.append("footer_synthetic must be false for LOCAL mode")

bundle_path_raw = m.get("bundle_path")
bundle_sha = m.get("bundle_sha256")
if not isinstance(bundle_path_raw, str) or not bundle_path_raw:
    errors.append("bundle_path missing")
else:
    bundle_path = pathlib.Path(bundle_path_raw).expanduser()
    if not bundle_path.exists() or not bundle_path.is_file():
        errors.append(f"bundle_path missing on disk: {bundle_path}")
    else:
        h = hashlib.sha256()
        with bundle_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        real = h.hexdigest()
        if bundle_sha != real:
            errors.append(f"bundle_sha256 mismatch: manifest={bundle_sha} real={real}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)

print("Local QA artifact gate passed.")
PY
