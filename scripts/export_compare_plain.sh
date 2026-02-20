#!/usr/bin/env bash
set -euo pipefail

cd /Users/cjarguello/bitpod
source .venv311/bin/activate

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY is required"
  exit 1
fi

VIDEO_URL="https://www.youtube.com/watch?v=BFt82dw0ci8"
ANCHOR_MP3="https://anchor.fm/s/e29097f4/podcast/play/115619664/https%3A%2F%2Fd3ctxlq1ktw2nl.cloudfront.net%2Fstaging%2F2026-1-17%2F418255357-44100-2-b07eb0f35b621.mp3"
OUT_DIR="/Users/cjarguello/bitpod/transcripts/jack_mallers_show/compare"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT_DIR" /Users/cjarguello/bitpod/cache/compare/youtube /Users/cjarguello/bitpod/cache/compare/anchor/chunks
echo "$STAMP" > /tmp/bitpod_stamp

python - <<'PY'
from pathlib import Path
from bitpod.audio import extract_youtube_captions
video_url = "https://www.youtube.com/watch?v=BFt82dw0ci8"
out = Path("/Users/cjarguello/bitpod/transcripts/jack_mallers_show/compare")
stamp = Path('/tmp/bitpod_stamp').read_text().strip()
work = Path("/Users/cjarguello/bitpod/cache/compare/youtube")
text = extract_youtube_captions(video_url, work, min_words=50)
if not text:
    raise SystemExit("Could not extract YouTube captions")
(out / f"{stamp}_youtube_plain.txt").write_text(text.strip() + "\n", encoding="utf-8")
print(out / f"{stamp}_youtube_plain.txt")
PY

# download anchor media once
curl -L --fail --silent --show-error "$ANCHOR_MP3" -o "/Users/cjarguello/bitpod/cache/compare/anchor/${STAMP}_anchor.mp3"

# split to API-safe chunks (8 minutes each)
ffmpeg -hide_banner -loglevel error -y \
  -i "/Users/cjarguello/bitpod/cache/compare/anchor/${STAMP}_anchor.mp3" \
  -f segment -segment_time 480 -c copy \
  "/Users/cjarguello/bitpod/cache/compare/anchor/chunks/${STAMP}_%03d.mp3"

python - <<'PY'
from pathlib import Path
from bitpod.transcribe import transcribe_audio
out = Path("/Users/cjarguello/bitpod/transcripts/jack_mallers_show/compare")
stamp = Path('/tmp/bitpod_stamp').read_text().strip()
chunk_dir = Path("/Users/cjarguello/bitpod/cache/compare/anchor/chunks")
parts = sorted(chunk_dir.glob(f"{stamp}_*.mp3"))
if not parts:
    raise SystemExit("No Anchor chunks produced")
texts = []
for p in parts:
    result = transcribe_audio(p, model="gpt-4o-mini-transcribe")
    texts.append(result.text.strip())
anchor_out = out / f"{stamp}_anchor_plain.txt"
anchor_out.write_text("\n\n".join(texts).strip() + "\n", encoding="utf-8")
print(anchor_out)
PY

echo "DONE"
ls -1 "$OUT_DIR" | tail -n 5
