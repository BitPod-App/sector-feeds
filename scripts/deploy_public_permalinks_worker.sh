#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_NAME="${1:-bitpod-public-permalinks-worker}"
SHOW_KEY="${2:-jack_mallers_show}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ -f "$REPO_ROOT/.bitpod_runtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_runtime.env"
  set +a
fi

cd "$REPO_ROOT"

echo "Refreshing public permalink artifacts from current run status"
"$PYTHON_BIN" "$REPO_ROOT/scripts/refresh_public_permalinks.py" "$SHOW_KEY"

echo "Deploying Worker + static assets"
npx wrangler deploy --config "$REPO_ROOT/cloudflare/permalinks-worker/wrangler.toml" --name "$WORKER_NAME"
