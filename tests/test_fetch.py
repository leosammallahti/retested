"""Pinned raw-input fetching must fail closed on an unexpected download."""
from __future__ import annotations

import hashlib
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import fetch


class _Response:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return self.data


class FetchTests(unittest.TestCase):
    def _manifest(self, expected: bytes, **entry_extra: str) -> dict:
        entry = {
            "path": "comparison.csv",
            "sha256": hashlib.sha256(expected).hexdigest(),
            "source_url": "https://example.test/comparison.csv",
        }
        entry.update(entry_extra)
        return {
            "files": [entry],
            "comparison_inputs": ["comparison.csv"],
        }

    def test_missing_drifted_download_is_not_saved_or_accepted_without_refresh(self):
        expected, drifted = b"pinned", b"upstream changed"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "raw"
            manifest_path = Path(directory) / "MANIFEST.json"
            original = self._manifest(expected)
            manifest_path.write_text(json.dumps(original), encoding="utf-8")
            with (
                mock.patch.object(fetch, "FORRT", root),
                mock.patch.object(fetch, "MANIFEST", manifest_path),
                mock.patch.object(fetch, "REQUIRED", []),
                mock.patch("urllib.request.urlopen", return_value=_Response(drifted)),
            ):
                self.assertEqual(fetch.run(), 1)
            self.assertFalse((root / "comparison.csv").exists())
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8")), original)

    def test_missing_matching_download_is_saved_and_then_validates(self):
        expected = b"pinned"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "raw"
            manifest_path = Path(directory) / "MANIFEST.json"
            manifest = self._manifest(expected)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with (
                mock.patch.object(fetch, "FORRT", root),
                mock.patch.object(fetch, "MANIFEST", manifest_path),
                mock.patch.object(fetch, "REQUIRED", []),
                mock.patch("urllib.request.urlopen", return_value=_Response(expected)),
            ):
                self.assertEqual(fetch.run(), 0)
                self.assertEqual(fetch.validate_inputs(root, manifest_path), [])
            self.assertEqual((root / "comparison.csv").read_bytes(), expected)

    def test_input_problems_identifies_missing_manifest_and_hash_mismatch(self):
        manifest = {"files": [], "comparison_inputs": ["comparison.csv"]}
        with mock.patch.object(fetch, "REQUIRED", []):
            self.assertEqual(
                fetch.input_problems(manifest, Path("/not-a-real-input-root")),
                ["required input absent from manifest: comparison.csv"],
            )

    def test_missing_input_restores_only_a_hash_verified_frozen_snapshot(self):
        expected = b"historical public bytes"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / "raw"
            snapshot = project / "snapshot.gz"
            snapshot.write_bytes(gzip.compress(expected, mtime=0))
            manifest_path = project / "MANIFEST.json"
            manifest_path.write_text(json.dumps(self._manifest(
                expected,
                frozen_snapshot="snapshot.gz",
                frozen_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )), encoding="utf-8")
            with (
                mock.patch.object(fetch, "FORRT", root),
                mock.patch.object(fetch, "ROOT", project),
                mock.patch.object(fetch, "MANIFEST", manifest_path),
                mock.patch.object(fetch, "REQUIRED", []),
                mock.patch("urllib.request.urlopen") as urlopen,
            ):
                self.assertEqual(fetch.run(), 0)
                self.assertEqual(fetch.validate_inputs(root, manifest_path), [])
                urlopen.assert_not_called()
            self.assertEqual((root / "comparison.csv").read_bytes(), expected)

    def test_mismatching_frozen_snapshot_is_not_written_or_downloaded(self):
        expected, wrong = b"historical public bytes", b"other bytes"
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            root = project / "raw"
            snapshot = project / "snapshot.gz"
            snapshot.write_bytes(gzip.compress(wrong, mtime=0))
            manifest_path = project / "MANIFEST.json"
            manifest_path.write_text(json.dumps(self._manifest(
                expected,
                frozen_snapshot="snapshot.gz",
                frozen_snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )), encoding="utf-8")
            with (
                mock.patch.object(fetch, "FORRT", root),
                mock.patch.object(fetch, "ROOT", project),
                mock.patch.object(fetch, "MANIFEST", manifest_path),
                mock.patch.object(fetch, "REQUIRED", []),
                mock.patch("urllib.request.urlopen") as urlopen,
            ):
                self.assertEqual(fetch.run(), 1)
                urlopen.assert_not_called()
            self.assertFalse((root / "comparison.csv").exists())


if __name__ == "__main__":
    unittest.main()
