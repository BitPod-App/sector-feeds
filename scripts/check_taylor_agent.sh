#!/usr/bin/env bash

set -euo pipefail

STRICT="${BITPOD_TAYLOR_AGENT_CHECK_STRICT:-0}"
TAYLOR_BIN="${TAYLOR_BIN:-}"

if [[ -z "${TAYLOR_BIN}" ]] && command -v taylor >/dev/null 2>&1; then
  TAYLOR_BIN="$(command -v taylor)"
fi

if [[ -z "${TAYLOR_BIN}" ]] || [[ ! -x "${TAYLOR_BIN}" ]]; then
  echo "Taylor agent check skipped: no installed taylor CLI (set TAYLOR_BIN or add taylor to PATH)"
  if [[ "${STRICT}" == "1" ]]; then
    exit 1
  fi
  exit 0
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
