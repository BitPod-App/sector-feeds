from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
