from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from bitpod.transcribe.base import TranscriptResult, TranscriptionProvider


class OpenAITranscriptionProvider(TranscriptionProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self.client = OpenAI(api_key=api_key)

    def transcribe_audio(self, path: str, model: str = "gpt-4o-mini-transcribe", **options: Any) -> TranscriptResult:
        try:
            response = self._transcribe(path, model, **options)
            model_used = model
        except Exception as exc:  # noqa: BLE001
            if not self._is_model_error(exc) or model == "whisper-1":
                raise
            response = self._transcribe(path, "whisper-1", **options)
            model_used = "whisper-1"

        text = getattr(response, "text", "") or ""
        segments = []
        raw_segments = getattr(response, "segments", None)
        if raw_segments:
            segments = [segment.model_dump() if hasattr(segment, "model_dump") else dict(segment) for segment in raw_segments]
        return TranscriptResult(text=text, model_used=model_used, segments=segments)

    def _transcribe(self, path: str, model: str, **options: Any) -> Any:
        with Path(path).open("rb") as audio_file:
            return self.client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                response_format=options.get("response_format", "verbose_json"),
                temperature=options.get("temperature", 0),
            )

    def _is_model_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        model_markers = ["model", "not found", "does not exist", "invalid"]
        return any(marker in text for marker in model_markers)
