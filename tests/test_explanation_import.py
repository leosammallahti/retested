"""Contracts for lossless, fail-closed explanation packet imports."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.explanation_import import import_packets, merge_records
from pipeline.explanations import ExplanationValidationError, validate_document

from tests.test_finding_explanations import DOI_O, document, promoted_row


def records(doc: dict) -> dict:
    return validate_document(doc, [promoted_row()])


class ExplanationImportTests(unittest.TestCase):
    def test_merges_new_records_and_exact_parallel_duplicates_deterministically(self) -> None:
        base = records({"schema_version": 1, "findings": {}})
        packet = records(document())
        # Packet order and evidence/support ordering have already been
        # canonicalized by the shared schema validator.
        merged, report = merge_records(
            base,
            [("packet-b.json", packet), ("packet-a.json", copy.deepcopy(packet))],
            {DOI_O},
        )
        self.assertEqual(list(merged["findings"]), [DOI_O])
        self.assertEqual(report.added, (DOI_O,))
        self.assertEqual(report.unchanged, (DOI_O,))
        self.assertEqual(report.total, 1)

    def test_conflicts_and_orphans_fail_before_any_write(self) -> None:
        packet = records(document())
        conflicting = copy.deepcopy(packet)
        conflicting[DOI_O]["original"]["claim"] = "A different source-reviewed original claim that conflicts materially."
        with self.assertRaisesRegex(ExplanationValidationError, "conflicting explanations"):
            merge_records(packet, [("parallel.json", conflicting)], {DOI_O})

        with self.assertRaisesRegex(ExplanationValidationError, "no built finding exists"):
            merge_records({}, [("orphan.json", packet)], set())

    def test_check_mode_is_non_mutating_and_write_mode_is_atomic_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "finding_explanations.json"
            packet_path = root / "packet.json"
            packet_path.write_text(json.dumps(document()), encoding="utf-8")

            checked = import_packets([packet_path], target, [promoted_row()], {DOI_O}, write=False)
            self.assertEqual(checked.added, (DOI_O,))
            self.assertFalse(target.exists())

            written = import_packets([packet_path], target, [promoted_row()], {DOI_O}, write=True)
            self.assertEqual(written.added, (DOI_O,))
            loaded = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(list(loaded["findings"]), [DOI_O])

            repeat = import_packets([packet_path], target, [promoted_row()], {DOI_O}, write=True)
            self.assertEqual(repeat.added, ())
            self.assertEqual(repeat.unchanged, (DOI_O,))

    def test_aliases_collapse_before_merge(self) -> None:
        packet = records(document())
        alias = {"10.9999/alias": packet[DOI_O]}
        existing = {DOI_O: packet[DOI_O]}
        merged, report = merge_records(
            existing, [("alias-packet.json", alias)], {DOI_O}, {"10.9999/alias": DOI_O},
        )
        self.assertEqual(list(merged["findings"]), [DOI_O])
        self.assertEqual(report.unchanged, (DOI_O,))


if __name__ == "__main__":
    unittest.main()
