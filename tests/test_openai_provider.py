from __future__ import annotations

import unittest
from unittest.mock import patch

from bitpod.transcribe.openai_provider import OpenAITranscriptionProvider


class OpenAIProviderErrorDetectionTests(unittest.TestCase):
    def test_payload_too_large_detection(self) -> None:
        provider = OpenAITranscriptionProvider.__new__(OpenAITranscriptionProvider)
        err = RuntimeError("Error code: 413 - Maximum content size limit (26214400) exceeded")
        self.assertTrue(provider._is_payload_too_large(err))

    def test_model_error_detection(self) -> None:
        provider = OpenAITranscriptionProvider.__new__(OpenAITranscriptionProvider)
        err = RuntimeError("The model does not exist")
        self.assertTrue(provider._is_model_error(err))

    def test_retryable_transcription_error_detection(self) -> None:
        provider = OpenAITranscriptionProvider.__new__(OpenAITranscriptionProvider)
        err = RuntimeError("Error code: 500 - Internal Server Error")
        self.assertTrue(provider._is_retryable_transcription_error(err))

    def test_transcribe_retries_on_retryable_server_error(self) -> None:
        provider = OpenAITranscriptionProvider.__new__(OpenAITranscriptionProvider)
        provider.TRANSIENT_RETRY_DELAYS_SECONDS = (0, 0)
        attempts: list[int] = []

        def _fake(path: str, model: str, **options):  # noqa: ANN001
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("Error code: 500 - Internal Server Error")
            return {"ok": True}

        provider._transcribe_with_payload_fallback = _fake  # type: ignore[method-assign]

        with patch("time.sleep", return_value=None):
            result = provider._transcribe_with_retries("sample.mp3", "gpt-4o-mini-transcribe")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(attempts), 3)

    def test_transcribe_does_not_retry_non_retryable_error(self) -> None:
        provider = OpenAITranscriptionProvider.__new__(OpenAITranscriptionProvider)
        provider.TRANSIENT_RETRY_DELAYS_SECONDS = (0, 0)
        attempts: list[int] = []

        def _fake(path: str, model: str, **options):  # noqa: ANN001
            attempts.append(1)
            raise RuntimeError("Error code: 401 - invalid_api_key")

        provider._transcribe_with_payload_fallback = _fake  # type: ignore[method-assign]

        with patch("time.sleep", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "invalid_api_key"):
                provider._transcribe_with_retries("sample.mp3", "gpt-4o-mini-transcribe")

        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
