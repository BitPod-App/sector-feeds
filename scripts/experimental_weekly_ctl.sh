#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
BITREGIME_CORE_ROOT="${BITREGIME_CORE_ROOT:-$WORKSPACE_ROOT/bitregime-core}"
PY="$REPO_ROOT/.venv311/bin/python"
SHOW_KEY="${SHOW_KEY:-jack_mallers_show}"
ART_ROOT="$REPO_ROOT/artifacts/private/experimental_weekly"
BITPOD_FEED_MODE="${BITPOD_FEED_MODE:-all}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/experimental_weekly_ctl.sh collect [--show <show_key>]
  bash scripts/experimental_weekly_ctl.sh process [--show <show_key>]
  bash scripts/experimental_weekly_ctl.sh render-legacy [--show <show_key>] [--label tuesday|friday|weekly]
  bash scripts/experimental_weekly_ctl.sh render-experimental --report-md <path> [--output-bundle <path>] [--output-gate <path>]

Notes:
  - This script is for the experimental decoupled track.
  - Legacy Tuesday flow remains unchanged and can still run directly.
EOF
}

parse_common_show() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --show)
        SHOW_KEY="$2"
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 2
        ;;
    esac
  done
}

cmd_collect() {
  parse_common_show "$@"
  mkdir -p "$ART_ROOT"
  cd "$REPO_ROOT"

  # Collect-only stage: discover feed metadata and snapshot current latest candidate.
  # Discovery is best-effort; when offline we still emit a local snapshot artifact.
  if [ "${EXPERIMENTAL_SKIP_DISCOVER:-0}" = "1" ]; then
    echo "INFO: skipping discover due to EXPERIMENTAL_SKIP_DISCOVER=1" >&2
  elif ! "$PY" -m bitpod discover --show "$SHOW_KEY"; then
    echo "WARN: discover failed; proceeding with local-only snapshot fallback." >&2
  fi
  "$PY" - "$SHOW_KEY" "$ART_ROOT" "$BITPOD_FEED_MODE" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from bitpod.config import get_show, load_config
from bitpod.feeds import parse_feed
from bitpod.sync import _choose_best_source, get_feed_urls

show_key = sys.argv[1]
art_root = Path(sys.argv[2])
feed_mode = sys.argv[3]
config = load_config()
show = get_show(config, show_key)
feed_urls = get_feed_urls(show, feed_mode=feed_mode)
episodes = []
parse_errors = []
for url in feed_urls:
    try:
        episodes.extend(parse_feed(url))
    except Exception as exc:  # noqa: BLE001
        parse_errors.append({"feed_url": url, "error": str(exc)})
deduped = {}
for ep in episodes:
    key = str(ep.guid)
    cur = deduped.get(key)
    deduped[key] = ep if cur is None else _choose_best_source(cur, ep)

latest = None
if deduped:
    latest = max(deduped.values(), key=lambda ep: ep.published_at)
else:
    # Local-only fallback: use last known status artifact if feed parsing fails.
    stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
    stem = Path(stable_pointer).stem
    status_json = Path("transcripts") / show_key / f"{stem}_status.json"
    if status_json.exists():
        payload = json.loads(status_json.read_text(encoding="utf-8"))
        latest = type(
            "FallbackEpisode",
            (),
            {
                "guid": payload.get("latest_episode_guid"),
                "title": payload.get("latest_episode_title"),
                "published_at": datetime.fromisoformat(str(payload.get("latest_episode_published_at_utc")).replace("Z", "+00:00"))
                if payload.get("latest_episode_published_at_utc")
                else datetime.min.replace(tzinfo=timezone.utc),
                "source_url": payload.get("attempted_source_url"),
                "source_type": payload.get("attempted_source_type") or "local_status_fallback",
            },
        )()

payload = {
    "contract_version": "experimental_intake_snapshot.v1",
    "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "show_key": show_key,
    "feed_mode": feed_mode,
    "feed_urls": feed_urls,
    "feed_parse_errors": parse_errors,
    "episode_count": len(deduped),
    "latest_episode": (
        {
            "guid": str(latest.guid),
            "title": latest.title,
            "published_at_utc": latest.published_at.astimezone(timezone.utc).isoformat(),
            "source_url": latest.source_url,
            "source_type": getattr(latest, "source_type", "unknown"),
        }
        if latest
        else None
    ),
}

# Attach shared permalink/discovery contract from latest show status when present.
stable_pointer = str(show.get("stable_pointer") or ("latest_bitpod.md" if show_key != "jack_mallers_show" else "jack_mallers.md"))
stem = Path(stable_pointer).stem
status_json = Path("transcripts") / show_key / f"{stem}_status.json"
if status_json.exists():
    try:
        s = json.loads(status_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        s = {}
    payload["shared_permalink_contract"] = {
        "ready_via_permalink": bool(s.get("ready_via_permalink")),
        "public_permalink_intake_url": s.get("public_permalink_intake_url"),
        "public_permalink_transcript_url": s.get("public_permalink_transcript_url"),
        "public_permalink_latest_url": s.get("public_permalink_latest_url"),
        "public_permalink_status_url": s.get("public_permalink_status_url"),
        "public_permalink_discovery_url": s.get("public_permalink_discovery_url"),
        "public_permalink_intake_path": s.get("public_permalink_intake_path"),
        "public_permalink_transcript_path": s.get("public_permalink_transcript_path"),
        "public_permalink_latest_path": s.get("public_permalink_latest_path"),
        "public_permalink_status_path": s.get("public_permalink_status_path"),
        "public_permalink_discovery_path": s.get("public_permalink_discovery_path"),
    }

out = art_root / f"{show_key}_intake_snapshot.json"
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
PY
}

cmd_process() {
  parse_common_show "$@"
  cd "$REPO_ROOT"
  # Process-only stage: update local transcript/pointer/permalink state if needed.
  bash "$SCRIPT_DIR/run_show_adhoc.sh" "$SHOW_KEY"
}

cmd_render_legacy() {
  local label="weekly"
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --show)
        SHOW_KEY="$2"
        shift 2
        ;;
      --label)
        label="$2"
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 2
        ;;
    esac
  done
  cd "$REPO_ROOT"
  bash "$SCRIPT_DIR/report_show_weekly_status.sh" "$SHOW_KEY" "$label"
}

cmd_render_experimental() {
  local report_md=""
  local output_bundle="$REPO_ROOT/artifacts/private/weekly_bundles/weekly_critical_bundle.json"
  local output_gate="$BITREGIME_CORE_ROOT/artifacts/gates/weekly_bundle_gate_status.json"

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --report-md)
        report_md="$2"
        shift 2
        ;;
      --output-bundle)
        output_bundle="$2"
        shift 2
        ;;
      --output-gate)
        output_gate="$2"
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 2
        ;;
    esac
  done

  if [ -z "$report_md" ]; then
    echo "Missing required --report-md <path>" >&2
    usage
    exit 2
  fi

  cd "$REPO_ROOT"
  python3 "$SCRIPT_DIR/generate_weekly_critical_bundle.py" \
    --report-md "$report_md" \
    --output-json "$output_bundle"

  python3 "$BITREGIME_CORE_ROOT/scripts/gate_weekly_bundle.py" \
    --bundle-json "$output_bundle" \
    --output-json "$output_gate"

  echo "bundle_json=$output_bundle"
  echo "gate_json=$output_gate"
}

if [ "$#" -lt 1 ]; then
  usage
  exit 2
fi

cmd="$1"
shift

case "$cmd" in
  collect)
    cmd_collect "$@"
    ;;
  process)
    cmd_process "$@"
    ;;
  render-legacy)
    cmd_render_legacy "$@"
    ;;
  render-experimental)
    cmd_render_experimental "$@"
    ;;
  *)
    echo "Unknown subcommand: $cmd" >&2
    usage
    exit 2
    ;;
esac
