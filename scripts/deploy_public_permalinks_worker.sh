#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_NAME="${1:-bitpod-public-permalinks-worker}"
SHOW_KEY="${2:-jack_mallers_show}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CANONICAL_BASE_URL="${BITPOD_PUBLIC_PERMALINK_BASE_URL:-https://permalinks.bitpod.app}"
CUSTOM_DOMAIN="${PERMALINKS_WORKER_CUSTOM_DOMAIN:-}"
WORKERS_DEV_BASE_URL="${PERMALINKS_WORKER_PREVIEW_BASE_URL:-}"
VERIFY_WRITE="${PERMALINKS_VERIFY_WRITE:-auto}"
DEPLOY_ARGS=(deploy --config "$REPO_ROOT/cloudflare/permalinks-worker/wrangler.toml" --name "$WORKER_NAME")

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
if [ -n "$CUSTOM_DOMAIN" ]; then
  DEPLOY_ARGS+=(--domains "$CUSTOM_DOMAIN")
fi

if ! DEPLOY_OUT="$(npx wrangler "${DEPLOY_ARGS[@]}" 2>&1)"; then
  echo "$DEPLOY_OUT"
  exit 1
fi
echo "$DEPLOY_OUT"

WORKERS_DEV_URL="$(printf '%s\n' "$DEPLOY_OUT" | grep -Eo 'https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev' | tail -n 1 || true)"
if [ -n "$WORKERS_DEV_URL" ]; then
  mkdir -p "$REPO_ROOT/artifacts/private/coordination"
  printf '%s\n' "$WORKERS_DEV_URL" > "$REPO_ROOT/artifacts/private/coordination/latest_worker_deploy_url.txt"
  echo "latest_worker_deploy_url_saved=$WORKERS_DEV_URL"
fi

if [ -z "$WORKERS_DEV_BASE_URL" ] && [ -n "$WORKERS_DEV_URL" ]; then
  WORKERS_DEV_BASE_URL="$WORKERS_DEV_URL"
fi

VERIFY_BASE_URL="$WORKERS_DEV_BASE_URL"
if [ -n "$CUSTOM_DOMAIN" ]; then
  VERIFY_BASE_URL="https://$CUSTOM_DOMAIN"
fi

if [ -z "$VERIFY_BASE_URL" ]; then
  echo "Could not determine Worker verification base URL."
  exit 2
fi

echo "Verifying Worker bundle readability via $VERIFY_BASE_URL"
VERIFY_ARGS=(
  --show "$SHOW_KEY"
  --base-url "$VERIFY_BASE_URL"
  --retries 18
  --retry-delay 5
)

WRITE_CANONICAL_STATUS=0
if [ "$VERIFY_WRITE" = "1" ] || { [ "$VERIFY_WRITE" = "auto" ] && [ -n "$CUSTOM_DOMAIN" ] && [ "$VERIFY_BASE_URL" = "$CANONICAL_BASE_URL" ]; }; then
  VERIFY_ARGS+=(--write)
  WRITE_CANONICAL_STATUS=1
fi

if ! "$PYTHON_BIN" "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" "${VERIFY_ARGS[@]}"; then
  if [ -n "$CUSTOM_DOMAIN" ] && [ -n "$WORKERS_DEV_BASE_URL" ]; then
    echo "Canonical verification failed from this runner. Falling back to preview-host verification before deciding deploy status."
    "$PYTHON_BIN" "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" \
      --show "$SHOW_KEY" \
      --base-url "$WORKERS_DEV_BASE_URL" \
      --retries 18 \
      --retry-delay 5
    echo "Warning: canonical custom-domain verification failed from CI, but preview Worker verification succeeded."
    echo "Treating deploy as successful because Worker deploy and preview readability are healthy; canonical domain may still be subject to edge-specific runner blocking or propagation lag."
    exit 0
  fi
  exit 1
fi

if [ "$WRITE_CANONICAL_STATUS" = "1" ]; then
  echo "Redeploying Worker after writing canonical bundle health"
  if ! DEPLOY_OUT="$(npx wrangler "${DEPLOY_ARGS[@]}" 2>&1)"; then
    echo "$DEPLOY_OUT"
    exit 1
  fi
  echo "$DEPLOY_OUT"

  echo "Final public verification via $VERIFY_BASE_URL"
  "$PYTHON_BIN" "$REPO_ROOT/scripts/verify_public_permalink_bundle.py" \
    --show "$SHOW_KEY" \
    --base-url "$VERIFY_BASE_URL" \
    --retries 18 \
    --retry-delay 5
fi
