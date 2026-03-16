#!/usr/bin/env bash

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
  echo "Missing dependency: rg (ripgrep). Install with: brew install ripgrep"
  exit 1
fi

DEFAULT_TOOLS_ROOTS=(
  "/Users/cjarguello/BitPod-App/tools"
  "/Users/cjarguello/bitpod-app/tools"
)

resolve_taylor_bin() {
  if [[ -n "${TAYLOR_BIN:-}" ]]; then
    printf '%s' "${TAYLOR_BIN}"
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
  echo "Missing Taylor runtime binary: ${TAYLOR_BIN}"
  echo "Checked defaults: ${DEFAULT_TOOLS_ROOTS[*]}"
  echo "Override with TOOLS_ROOT=/path/to/tools or TAYLOR_BIN=/path/to/taylor"
  exit 1
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
