#!/usr/bin/env bash
set -euo pipefail

SHOW_KEY="${1:-jack_mallers_show}"
BASE_URL="${2:-https://permalinks.bitpod.app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python3 "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" --show "$SHOW_KEY" --base-url "$BASE_URL"
