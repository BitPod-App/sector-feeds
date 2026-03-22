from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.refresh_public_permalinks as refresh_module


class RefreshPublicPermalinksTests(unittest.TestCase):
    def test_remote_status_urls_prefers_canonical_then_preview_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            coordination_dir = repo_root / "artifacts" / "private" / "coordination"
            coordination_dir.mkdir(parents=True, exist_ok=True)
            (coordination_dir / "latest_worker_deploy_url.txt").write_text(
                "https://bitpod-public-permalinks-worker.example.workers.dev\n",
                encoding="utf-8",
            )

            with mock.patch.object(refresh_module, "REPO_ROOT", repo_root), \
                mock.patch.object(refresh_module, "_public_permalink_id", return_value="opaque123"), \
                mock.patch.object(refresh_module, "_public_permalink_base_url", return_value="https://permalinks.bitpod.app"), \
                mock.patch.dict(os.environ, {"PERMALINKS_WORKER_PREVIEW_BASE_URL": "https://preview.example.workers.dev"}, clear=False):
                urls = refresh_module._remote_status_urls("jack_mallers_show")

        self.assertEqual(
            urls,
            [
                "https://permalinks.bitpod.app/opaque123/status.json",
                "https://bitpod-public-permalinks-worker.example.workers.dev/opaque123/status.json",
                "https://preview.example.workers.dev/opaque123/status.json",
            ],
        )


if __name__ == "__main__":
    unittest.main()
