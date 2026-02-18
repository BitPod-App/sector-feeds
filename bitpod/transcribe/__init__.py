from __future__ import annotations

from pathlib import Path
from typing import Any

from bitpod.transcribe.base import TranscriptResult
from bitpod.transcribe.openai_provider import OpenAITranscriptionProvider


def transcribe_audio(path: Path, model: str = "gpt-4o-mini-transcribe", **options: Any) -> TranscriptResult:
    provider = OpenAITranscriptionProvider(api_key=options.pop("api_key", None))
    return provider.transcribe_audio(str(path), model=model, **options)
