from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.pair_match_reconcile import reconcile, write_reconciliation


class PairMatchReconcileTests(unittest.TestCase):
    def _inputs(self, root: Path) -> tuple[Path, Path]:
        audit = root / "audit.json"
        ledger = root / "ledger.json"
        audit.write_text(json.dumps({"records": [
            {"doi_o": "10.1000/o1", "doi_r": "10.1000/r1", "combined_classification": "no_exact_doi_or_title_match"},
            {"doi_o": "10.1000/o2", "doi_r": "10.1000/r2", "combined_classification": "no_exact_doi_or_title_match"},
            {"doi_o": "10.1000/o3", "doi_r": "10.1000/r3", "combined_classification": "later_paper_recorded_pair_unconfirmed"},
        ]}), encoding="utf-8")
        ledger.write_text(json.dumps({"decisions": [
            {
                "query_record_id": "q1", "doi_o": "10.1000/o1", "doi_r": "10.1000/r1",
                "decision": "confirmed_same_later_version_same_pair", "candidate_record_ids": ["c1"],
                "independent_work_identity_review": {
                    "second_review_status": "agree", "scientific_equivalence_axes": "not_compared",
                },
            },
            {
                "query_record_id": "q2", "doi_o": "10.1000/o2", "doi_r": "10.1000/r2",
                "decision": "same_later_work_different_original", "candidate_record_ids": ["c2"],
            },
            {
                "query_record_id": "q3", "doi_o": "10.1000/o3", "doi_r": "10.1000/r3",
                "decision": "related_but_distinct", "candidate_record_ids": ["c3"],
            },
        ]}), encoding="utf-8")
        return audit, ledger

    def test_only_positive_decisions_strengthen_the_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audit, ledger = self._inputs(root)
            payload = reconcile(audit, ledger)
            summary = payload["summary"]
            self.assertEqual(summary["same_pair_recorded"], 1)
            self.assertEqual(summary["later_paper_recorded_pair_unconfirmed"], 2)
            self.assertEqual(summary["no_exact_doi_or_title_match"], 0)
            self.assertEqual(summary["candidate_new_pair_links"], 2)
            self.assertEqual(payload["records"][2]["reconciled_classification"], "later_paper_recorded_pair_unconfirmed")
            self.assertEqual(payload["records"][2]["semantic_adjudication"]["decision"], "related_but_distinct")
            self.assertEqual(
                payload["records"][0]["semantic_adjudication"]["independent_work_identity_review"]["second_review_status"],
                "agree",
            )

            output = root / "output.json"
            write_reconciliation(payload, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

    def test_rejects_adjudication_absent_from_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            audit, ledger = self._inputs(root)
            data = json.loads(ledger.read_text(encoding="utf-8"))
            data["decisions"][0]["doi_r"] = "10.1000/not-in-audit"
            ledger.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "absent from overlap audit"):
                reconcile(audit, ledger)


if __name__ == "__main__":
    unittest.main()
