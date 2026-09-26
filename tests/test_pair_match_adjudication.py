from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.pair_match_adjudication import build_ledger, write_ledger


class PairMatchAdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.queue = self.root / "queue.json"
        self.queue.write_text(json.dumps({"records": [{
            "query": {"id": "query-1", "doi_o": "10.1/o", "doi_r": "10.1/r"},
            "prior_classification": "no_exact_match",
            "top_score": 0.97,
            "candidates": [{"record_id": "candidate-1", "record": {"doi_r": "10.1/candidate"}}],
        }]}), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def _decisions(self, row: dict) -> Path:
        path = self.root / "decisions.json"
        path.write_text(json.dumps({"reviewed_at_utc": "2026-09-26T00:00:00Z", "decisions": [row]}), encoding="utf-8")
        return path

    def test_normalizes_and_preserves_parallel_reviewer_schema(self):
        decisions = self._decisions({
            "query_id": "query-1",
            "decision": "confirmed_same_later_version_same_pair",
            "candidate_assessments": [{"record_id": "candidate-1", "relation": "journal version"}],
            "evidence": "The preprint and article report the same study.",
            "sources": [{"path": "source.csv", "row": 4}],
        })
        payload = build_ledger(self.queue, [decisions])
        row = payload["decisions"][0]
        self.assertEqual(payload["summary"]["reviewed_queries"], 1)
        self.assertEqual(payload["summary"]["counts"]["confirmed_same_later_version_same_pair"], 1)
        self.assertEqual(row["candidate_record_ids"], ["candidate-1"])
        self.assertEqual(row["query_snapshot"]["id"], "query-1")
        self.assertEqual(row["candidate_snapshots"][0]["record"]["doi_r"], "10.1/candidate")
        self.assertTrue(row["original_work_matches"])
        self.assertTrue(row["later_work_matches"])
        self.assertEqual(row["reviewer_record"]["candidate_assessments"][0]["relation"], "journal version")
        self.assertEqual(len(payload["frozen_queue"]["sha256"]), 64)

        output = self.root / "ledger.json"
        write_ledger(payload, output)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

    def test_rejects_unknown_candidate_and_duplicate_query(self):
        unknown = self._decisions({
            "query_record_id": "query-1",
            "decision": "confirmed_same_pair",
            "candidate_record_ids": ["not-in-queue"],
        })
        with self.assertRaisesRegex(ValueError, "absent from frozen queue"):
            build_ledger(self.queue, [unknown])

        first = self._decisions({
            "query_record_id": "query-1",
            "decision": "related_but_distinct",
            "candidate_record_ids": ["candidate-1"],
        })
        second = self.root / "second.json"
        second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reviewed more than once"):
            build_ledger(self.queue, [first, second])


if __name__ == "__main__":
    unittest.main()
