"""The normal build must refresh and validate reconciliation artifacts."""
from __future__ import annotations

import unittest
from unittest import mock

from pipeline import __main__ as cli


class BuildReconciliationTests(unittest.TestCase):
    def test_refreshes_pinned_pair_summaries_before_writing_registry(self):
        events: list[str] = []
        summaries = {"query_records": [{"id": "query"}], "corpus_records": [{"id": "corpus"}]}
        registry = {"counts": {"retested_normalized_pairs": 1}}

        with (
            mock.patch.object(cli.pair_summaries, "regenerate_default_document", return_value=summaries) as refresh,
            mock.patch.object(cli.reconciliation_registry, "generate_and_write", return_value=(registry, [])) as write,
        ):
            problems = cli.build_reconciliation_artifacts(events.append)

        self.assertEqual(problems, [])
        refresh.assert_called_once_with()
        write.assert_called_once_with()
        self.assertEqual(len(events), 2)
        self.assertIn("pair summaries", events[0])
        self.assertIn("structural=PASS assurance=INCOMPLETE", events[1])

    def test_returns_structural_problems_without_calling_the_result_a_success(self):
        summaries = {"query_records": [], "corpus_records": []}
        events: list[str] = []
        with (
            mock.patch.object(cli.pair_summaries, "regenerate_default_document", return_value=summaries),
            mock.patch.object(
                cli.reconciliation_registry,
                "generate_and_write",
                return_value=(None, ["pinned source file hash mismatch"]),
            ),
        ):
            problems = cli.build_reconciliation_artifacts(events.append)

        self.assertEqual(problems, ["pinned source file hash mismatch"])
        self.assertEqual(len(events), 1)
        self.assertIn("pair summaries", events[0])


if __name__ == "__main__":
    unittest.main()
