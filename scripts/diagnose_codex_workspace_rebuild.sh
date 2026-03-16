#!/usr/bin/env bash
set -euo pipefail

canonical_roots=(
  "/Users/cjarguello/BitPod-App"
  "/Users/cjarguello/bitpod-app"
)

resolve_workspace_root() {
  if [[ -n "${1:-}" ]]; then
    printf '%s' "$1"
    return
  fi

  local candidate=""
  for candidate in "${canonical_roots[@]}"; do
    if [[ -d "$candidate" ]]; then
      printf '%s' "$candidate"
      return
    fi
  done

  printf '%s' "$HOME/BitPod-App"
}

workspace_root="$(resolve_workspace_root "${1:-}")"

section() {
  printf '\n== %s ==\n' "$1"
}

warn() {
  printf 'WARN: %s\n' "$1"
}

ok() {
  printf 'OK: %s\n' "$1"
}

section "Workspace root"
printf 'Target: %s\n' "$workspace_root"
if [[ ! -d "$workspace_root" ]]; then
  echo "ERROR: workspace root not found"
  echo "Hint: pass explicit root path as first argument."
  exit 1
fi

if [[ -d "$workspace_root/.codex" ]]; then
  ok "workspace .codex exists"
else
  warn "workspace .codex is missing"
fi

section "Root Codex config"
for f in .codex/org-workspace.toml .codex/environments/environment.toml .codex/policy.md; do
  if [[ -f "$workspace_root/$f" ]]; then
    ok "$f"
  else
    warn "$f missing"
  fi
done

if [[ -f "$workspace_root/.codex/org-workspace.toml" ]]; then
  current_root=$(awk -F' = ' '/^root_path/{gsub(/"/,"",$2);print $2}' "$workspace_root/.codex/org-workspace.toml" || true)
  printf 'Configured root_path: %s\n' "${current_root:-<unset>}"
  if [[ "$current_root" == "${canonical_roots[0]}" || "$current_root" == "${canonical_roots[1]}" ]]; then
    ok "root_path matches allowed canonical roots"
  else
    warn "root_path differs from allowed canonical roots (${canonical_roots[*]})"
  fi
fi

section "Repo-local .codex/config.toml"
repos=(.github bitpod-assets bitpod-docs bitpod-taylor-runtime bitpod-tools bitregime-core linear sector-feeds)
missing=0
for repo in "${repos[@]}"; do
  cfg="$workspace_root/$repo/.codex/config.toml"
  if [[ -f "$cfg" ]]; then
    ok "$repo/.codex/config.toml"
  else
    warn "$repo/.codex/config.toml missing"
    ((missing+=1))
  fi
done
printf 'Missing repo config count: %d\n' "$missing"

section "Stale path references in workspace .codex"
if command -v rg >/dev/null 2>&1; then
  rg -n "/Users/cjarguello/bitpod-app-rebuild|/Users/cjarguello/bitpod-app-retired" \
    "$workspace_root/.codex" "$workspace_root"/*/.codex 2>/dev/null || true
else
  warn "ripgrep not found; skipping stale path scan"
fi

section "Taylor health-check script location"
if [[ -f "$workspace_root/scripts/check_taylor_skill.sh" && -f "$workspace_root/scripts/check_taylor_agent.sh" ]]; then
  ok "Taylor health-check scripts exist at workspace root"
else
  warn "Taylor health-check scripts are not in workspace root"
  if [[ -f "$workspace_root/sector-feeds/scripts/check_taylor_skill.sh" && -f "$workspace_root/sector-feeds/scripts/check_taylor_agent.sh" ]]; then
    ok "Taylor health-check scripts exist in workspace repo: sector-feeds/scripts"
    printf 'Run: (cd "%s/sector-feeds" && bash scripts/check_taylor_skill.sh && bash scripts/check_taylor_agent.sh)\n' "$workspace_root"
  else
    warn "Could not locate Taylor health-check scripts under workspace root or sector-feeds"
  fi
fi

section "Git remotes"
for repo in "${repos[@]}"; do
  if [[ -d "$workspace_root/$repo/.git" ]]; then
    remote=$(git -C "$workspace_root/$repo" remote get-url origin 2>/dev/null || true)
    branch=$(git -C "$workspace_root/$repo" branch --show-current 2>/dev/null || true)
    printf '%s: origin=%s branch=%s\n' "$repo" "${remote:-<none>}" "${branch:-<none>}"
  else
    warn "$repo is missing .git"
  fi
done

section "Summary"
printf 'If only stale references are inside .codex/skills/*.md, they are low-risk docs and not launch blockers.\n'
printf 'Primary blockers are usually missing .codex root files, bad root_path, or stale app-registered project paths.\n'
