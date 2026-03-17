#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/artifacts/public/permalinks"
PROJECT_NAME="${1:-bitpod-public-permalinks}"
BRANCH_NAME="${2:-main}"
SHOW_KEY="${3:-jack_mallers_show}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d "$DEPLOY_DIR" ]; then
  echo "Missing deploy directory: $DEPLOY_DIR"
  echo "Run sync first to generate public permalink artifacts."
  exit 2
fi

# Optional local runtime secrets.
if [ -f "$REPO_ROOT/.bitpod_runtime.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_runtime.env"
  set +a
fi

CANONICAL_BASE_URL="${BITPOD_PUBLIC_PERMALINK_BASE_URL:-https://bitpod-public-permalinks.pages.dev}"

echo "Refreshing public permalink artifacts from current run status"
"$PYTHON_BIN" "$REPO_ROOT/scripts/refresh_public_permalinks.py" "$SHOW_KEY"

echo "Deploying '$DEPLOY_DIR' to Cloudflare Pages project '$PROJECT_NAME' (branch '$BRANCH_NAME')"
npx wrangler whoami
DEPLOY_OUT="$(npx wrangler pages deploy "$DEPLOY_DIR" --project-name "$PROJECT_NAME" --branch "$BRANCH_NAME" 2>&1)"
echo "$DEPLOY_OUT"

LATEST_URL="$(printf '%s\n' "$DEPLOY_OUT" | grep -Eo 'https://[a-z0-9]+\.bitpod-public-permalinks\.pages\.dev' | tail -n 1 || true)"
if [ -n "$LATEST_URL" ]; then
  mkdir -p "$REPO_ROOT/artifacts/coordination"
  printf '%s\n' "$LATEST_URL" > "$REPO_ROOT/artifacts/coordination/latest_deploy_url.txt"
  echo "latest_deploy_url_saved=$LATEST_URL"
fi

echo "Verifying canonical public bundle readability via $CANONICAL_BASE_URL"
"$PYTHON_BIN" "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" --show "$SHOW_KEY" --base-url "$CANONICAL_BASE_URL" --write

echo "Redeploying updated status.json bundle health"
DEPLOY_OUT="$(npx wrangler pages deploy "$DEPLOY_DIR" --project-name "$PROJECT_NAME" --branch "$BRANCH_NAME" --commit-dirty=true 2>&1)"
echo "$DEPLOY_OUT"

echo "Final public verification"
"$PYTHON_BIN" "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" --show "$SHOW_KEY" --base-url "$CANONICAL_BASE_URL"
