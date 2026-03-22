#!/usr/bin/env bash

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "Missing dependency: rg (ripgrep). Install with: brew install ripgrep"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_root="$(cd "${repo_root}/.." && pwd)"
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

DEFAULT_TOOLS_ROOTS=(
  "${repo_root}/../tools"
  "${repo_root}/../bitpod-tools/tools"
  "${workspace_root}/tools"
)

resolve_taylor_bin() {
  if [[ -n "${TAYLOR_BIN:-}" ]]; then
    printf '%s' "${TAYLOR_BIN}"
    return
  fi

  if command -v taylor >/dev/null 2>&1; then
    command -v taylor
    return
  fi

  if [[ -n "${TOOLS_ROOT:-}" ]]; then
    printf '%s' "${TOOLS_ROOT}/taylor/bin/taylor"
    return
  fi

  local root=""
  for root in "${DEFAULT_TOOLS_ROOTS[@]}"; do
    if [[ -x "${root}/taylor/bin/taylor" ]]; then
      printf '%s' "${root}/taylor/bin/taylor"
      return
    fi
  done

  printf '%s' "${DEFAULT_TOOLS_ROOTS[0]}/taylor/bin/taylor"
}

TAYLOR_BIN="$(resolve_taylor_bin)"

if [[ ! -x "${TAYLOR_BIN}" ]]; then
  skip_or_fail "Taylor runtime binary not found at ${TAYLOR_BIN}. Checked defaults: ${DEFAULT_TOOLS_ROOTS[*]}. Override with TOOLS_ROOT=/path/to/tools or TAYLOR_BIN=/path/to/taylor"
fi

echo "Using Taylor runtime: ${TAYLOR_BIN}"

WHOAMI_OUT="$(${TAYLOR_BIN} whoami)"
if [[ -z "${WHOAMI_OUT}" ]]; then
  echo "taylor whoami returned empty output"
  exit 1
fi

echo "${WHOAMI_OUT}" | rg -q "Taylor version:" || { echo "Missing Taylor version in whoami output"; exit 1; }
echo "${WHOAMI_OUT}" | rg -q "Contract path:" || { echo "Missing contract path in whoami output"; exit 1; }
echo "${WHOAMI_OUT}" | rg -q "LOCAL: available" || { echo "LOCAL mode not reported as available"; exit 1; }

SELF_OUT="$(${TAYLOR_BIN} self-test --out-root /tmp)"
if [[ -z "${SELF_OUT}" ]]; then
  echo "taylor self-test returned empty output"
  exit 1
fi

echo "${SELF_OUT}" | rg -q "PASS" || { echo "self-test did not PASS"; exit 1; }
echo "${SELF_OUT}" | rg -q "Artifacts:" || { echo "self-test did not report artifact path"; exit 1; }

echo "Taylor agent check passed."
