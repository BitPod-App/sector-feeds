#!/usr/bin/env bash

set -euo pipefail

TOOLS_ROOT="${TOOLS_ROOT:-/Users/cjarguello/BitPod-App/tools}"
TAYLOR_BIN="${TAYLOR_BIN:-${TOOLS_ROOT}/taylor/bin/taylor}"

if [[ ! -x "${TAYLOR_BIN}" ]]; then
  echo "Missing Taylor runtime binary: ${TAYLOR_BIN}"
  exit 1
fi

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
