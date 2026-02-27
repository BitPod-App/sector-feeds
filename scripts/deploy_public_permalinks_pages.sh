#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DIR="$REPO_ROOT/artifacts/public/permalinks"
PROJECT_NAME="${1:-bitpod-public-permalinks}"
BRANCH_NAME="${2:-main}"

if [ ! -d "$DEPLOY_DIR" ]; then
  echo "Missing deploy directory: $DEPLOY_DIR"
  echo "Run sync first to generate public permalink artifacts."
  exit 2
fi

# Optional local runtime secrets.
if [ -f "$REPO_ROOT/.bitpod_runtime.env" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.bitpod_runtime.env"
fi

echo "Deploying '$DEPLOY_DIR' to Cloudflare Pages project '$PROJECT_NAME' (branch '$BRANCH_NAME')"
npx wrangler whoami
npx wrangler pages deploy "$DEPLOY_DIR" --project-name "$PROJECT_NAME" --branch "$BRANCH_NAME"
