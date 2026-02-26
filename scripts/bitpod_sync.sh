#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$REPO_ROOT/.bitpod_runtime.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_runtime.env"
elif [ -f "$REPO_ROOT/scripts/bitpod_runtime.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/scripts/bitpod_runtime.env"
fi

cd "$REPO_ROOT"
.venv311/bin/python scripts/bitpod_ctl.py sync "$@"
