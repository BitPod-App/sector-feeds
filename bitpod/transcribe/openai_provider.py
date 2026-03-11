from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from bitpod.transcribe.base import TranscriptResult, TranscriptionProvider

LOGGER = logging.getLogger(__name__)
MAX_TRANSCRIBE_BYTES = 25 * 1024 * 1024
TARGET_BYTES = 24 * 1024 * 1024


class OpenAITranscriptionProvider(TranscriptionProvider):
    TRANSIENT_RETRY_DELAYS_SECONDS = (2, 5)

    def __init__(self, api_key: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key)

    def transcribe_audio(self, path: str, model: str = "gpt-4o-mini-transcribe", **options: Any) -> TranscriptResult:
        try:
            response = self._transcribe_with_retries(path, model, **options)
            model_used = model
        except Exception as exc:  # noqa: BLE001
            if not self._is_model_error(exc) or model == "whisper-1":
                raise
            response = self._transcribe_with_retries(path, "whisper-1", **options)
            model_used = "whisper-1"

        text = getattr(response, "text", "") or ""
        segments = []
        raw_segments = getattr(response, "segments", None)
        if raw_segments:
            segments = [segment.model_dump() if hasattr(segment, "model_dump") else dict(segment) for segment in raw_segments]
        return TranscriptResult(text=text, model_used=model_used, segments=segments)

    def _transcribe(self, path: str, model: str, **options: Any) -> Any:
        stop = threading.Event()
        start = time.monotonic()

        def _heartbeat() -> None:
            while not stop.wait(15):
                elapsed = int(time.monotonic() - start)
                LOGGER.info("Transcription in progress (%ss elapsed, model=%s)...", elapsed, model)

        monitor = threading.Thread(target=_heartbeat, daemon=True)
        monitor.start()
        with Path(path).open("rb") as audio_file:
            try:
                return self.client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format=options.get("response_format", "verbose_json"),
                    temperature=options.get("temperature", 0),
                )
            finally:
                stop.set()

    def _transcribe_with_payload_fallback(self, path: str, model: str, **options: Any) -> Any:
        try:
            return self._transcribe(path, model, **options)
        except Exception as exc:  # noqa: BLE001
            if not self._is_payload_too_large(exc):
                raise
            LOGGER.warning("Transcription payload too large; compressing audio and retrying once: %s", path)
            temp_dir, compressed = self._compress_audio_for_transcription(path)
            try:
                return self._transcribe(str(compressed), model, **options)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _transcribe_with_retries(self, path: str, model: str, **options: Any) -> Any:
        delays = self.TRANSIENT_RETRY_DELAYS_SECONDS
        attempt = 0
        while True:
            try:
                return self._transcribe_with_payload_fallback(path, model, **options)
            except Exception as exc:  # noqa: BLE001
                if attempt >= len(delays) or not self._is_retryable_transcription_error(exc):
                    raise
                delay = delays[attempt]
                attempt += 1
                LOGGER.warning(
                    "Transient transcription failure for %s on attempt %s/%s; retrying in %ss: %s",
                    path,
                    attempt,
                    len(delays) + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)

    def _compress_audio_for_transcription(self, path: str) -> tuple[Path, Path]:
        source = Path(path)
        temp_dir = Path(tempfile.mkdtemp(prefix="bitpod-transcribe-"))
        output = temp_dir / f"{source.stem}.m4a"
        # Step-down ladder to stay under API max upload size.
        bitrates = ["24k", "20k", "16k", "12k", "8k"]
        last_err = ""
        for bitrate in bitrates:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "12000",
                "-c:a",
                "aac",
                "-b:a",
                bitrate,
                str(output),
            ]
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode != 0:
                last_err = completed.stderr[-800:]
                continue
            if not output.exists():
                last_err = "ffmpeg returned success but output file is missing"
                continue

            size = output.stat().st_size
            LOGGER.info("Compressed audio candidate (%s): %s bytes", bitrate, size)
            if size <= TARGET_BYTES:
                LOGGER.info("Compressed audio accepted for transcription: %s", output)
                return temp_dir, output

        raise RuntimeError(
            f"ffmpeg compression did not reach size target <= {TARGET_BYTES} bytes; last_error={last_err}"
        )

    def _is_model_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        explicit_model_markers = [
            "model does not exist",
            "the model does not exist",
            "model not found",
            "unknown model",
            "unsupported model",
            "invalid model",
            "model is not supported",
        ]
        return any(marker in text for marker in explicit_model_markers)

    def _is_payload_too_large(self, exc: Exception) -> bool:
        text = str(exc).lower()
        markers = ["413", "payload too large", "maximum content size limit", "content size limit"]
        return any(marker in text for marker in markers)

    def _is_retryable_transcription_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        markers = [
            "error code: 500",
            "error code: 502",
            "error code: 503",
            "error code: 504",
            "internal server error",
            "gateway timeout",
            "service unavailable",
            "timed out",
            "timeout",
            "connection error",
        ]
        return any(marker in text for marker in markers)
