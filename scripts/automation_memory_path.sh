#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/automation_memory_path.sh resolve <automation_id>
  bash scripts/automation_memory_path.sh ensure <automation_id>
  bash scripts/automation_memory_path.sh migrate <automation_id> [--from <path>] [--copy]
  bash scripts/automation_memory_path.sh verify-root

Environment (all optional):
  BITPOD_WORKSPACE_ROOT
  BITPOD_LOCAL_WORKSPACE_ROOT
  BITPOD_CODEX_STATE_ROOT
  BITPOD_AUTOMATION_MEMORY_ROOT
  BITPOD_BACKUP_WORKSPACE_ROOT
  BITPOD_EXTRA_ALLOWED_WRITE_ROOTS (colon-separated)
USAGE
}

if [ "$#" -lt 1 ]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_APP_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
HOME_APP_ROOT="${HOME}/bitpod-app"
if [ -d "$HOME_APP_ROOT/local-workspace" ]; then
  DEFAULT_APP_ROOT="$HOME_APP_ROOT"
elif [ -d "$DEFAULT_APP_ROOT/local-workspace" ]; then
  DEFAULT_APP_ROOT="$DEFAULT_APP_ROOT"
fi

BITPOD_WORKSPACE_ROOT="${BITPOD_WORKSPACE_ROOT:-$DEFAULT_APP_ROOT}"
BITPOD_LOCAL_WORKSPACE_ROOT="${BITPOD_LOCAL_WORKSPACE_ROOT:-$BITPOD_WORKSPACE_ROOT/local-workspace}"
BITPOD_CODEX_STATE_ROOT="${BITPOD_CODEX_STATE_ROOT:-$BITPOD_LOCAL_WORKSPACE_ROOT/local-codex/.codex}"
BITPOD_AUTOMATION_MEMORY_ROOT="${BITPOD_AUTOMATION_MEMORY_ROOT:-$BITPOD_CODEX_STATE_ROOT/automations}"

realpath_py() {
  python3 - "$1" <<'PY'
import pathlib
import sys

print(pathlib.Path(sys.argv[1]).expanduser().resolve())
PY
}

starts_with_path() {
  local target="$1"
  local root="$2"
  case "$target" in
    "$root"|"$root"/*) return 0 ;;
    *) return 1 ;;
  esac
}

assert_allowed_path() {
  local target="$1"
  local target_real
  target_real="$(realpath_py "$target")"

  local allowed=()
  allowed+=("$(realpath_py "$BITPOD_WORKSPACE_ROOT")")
  if [ -n "${BITPOD_BACKUP_WORKSPACE_ROOT:-}" ]; then
    allowed+=("$(realpath_py "$BITPOD_BACKUP_WORKSPACE_ROOT")")
  fi
  if [ -n "${BITPOD_EXTRA_ALLOWED_WRITE_ROOTS:-}" ]; then
    local root
    IFS=':' read -r -a extra <<<"$BITPOD_EXTRA_ALLOWED_WRITE_ROOTS"
    for root in "${extra[@]}"; do
      [ -z "$root" ] && continue
      allowed+=("$(realpath_py "$root")")
    done
  fi

  local root
  for root in "${allowed[@]}"; do
    if starts_with_path "$target_real" "$root"; then
      return 0
    fi
  done

  echo "Refusing path outside approved roots: $target_real" >&2
  echo "Approved roots:" >&2
  for root in "${allowed[@]}"; do
    echo "  - $root" >&2
  done
  exit 1
}

memory_path_for() {
  local automation_id="$1"
  if [ -z "$automation_id" ]; then
    echo "automation_id cannot be empty" >&2
    exit 2
  fi
  echo "$BITPOD_AUTOMATION_MEMORY_ROOT/$automation_id/memory.md"
}

cmd="$1"
shift || true

case "$cmd" in
  resolve)
    [ "$#" -eq 1 ] || { usage >&2; exit 2; }
    path="$(memory_path_for "$1")"
    assert_allowed_path "$path"
    echo "$path"
    ;;
  ensure)
    [ "$#" -eq 1 ] || { usage >&2; exit 2; }
    path="$(memory_path_for "$1")"
    assert_allowed_path "$path"
    mkdir -p "$(dirname "$path")"
    touch "$path"
    echo "$path"
    ;;
  migrate)
    [ "$#" -ge 1 ] || { usage >&2; exit 2; }
    automation_id="$1"
    shift || true

    source_path="${CODEX_HOME:-$HOME/.codex}/automations/$automation_id/memory.md"
    mode="move"
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --from)
          source_path="${2:-}"
          shift 2
          ;;
        --copy)
          mode="copy"
          shift
          ;;
        *)
          echo "Unknown option: $1" >&2
          usage >&2
          exit 2
          ;;
      esac
    done

    target_path="$(memory_path_for "$automation_id")"
    assert_allowed_path "$target_path"
    mkdir -p "$(dirname "$target_path")"

    if [ ! -f "$source_path" ]; then
      echo "Source not found; nothing to migrate: $source_path"
      echo "target=$target_path"
      exit 0
    fi

    if [ "$mode" = "copy" ]; then
      cp "$source_path" "$target_path"
      echo "migrated=copy"
    else
      mv "$source_path" "$target_path"
      echo "migrated=move"
    fi
    echo "source=$source_path"
    echo "target=$target_path"
    ;;
  verify-root)
    echo "repo_root=$REPO_ROOT"
    echo "bitpod_workspace_root=$BITPOD_WORKSPACE_ROOT"
    echo "bitpod_local_workspace_root=$BITPOD_LOCAL_WORKSPACE_ROOT"
    echo "bitpod_codex_state_root=$BITPOD_CODEX_STATE_ROOT"
    echo "bitpod_automation_memory_root=$BITPOD_AUTOMATION_MEMORY_ROOT"
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage >&2
    exit 2
    ;;
esac
