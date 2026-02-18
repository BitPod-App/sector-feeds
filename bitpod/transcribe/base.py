from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptResult:
    text: str
    model_used: str
    segments: list[dict[str, Any]] = field(default_factory=list)


class TranscriptionProvider:
    def transcribe_audio(self, path: str, model: str, **options: Any) -> TranscriptResult:
        raise NotImplementedError
