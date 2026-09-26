from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.pair_match_queue import build_queue, write_queue


class PairMatchQueueTests(unittest.TestCase):
    def _files(self, folder: Path) -> tuple[Path, Path]:
        rankings = folder / "rankings.json"
        audit = folder / "audit.json"
        rankings.write_text(json.dumps({
            "corpus_records": [{"id": "candidate", "doi_o": "10.1/o", "doi_r": "10.1/r"}],
            "queries": [{
                "query": {
                    "id": "query",
                    "doi_o": "10.1002/(SICI)1098-108X(199809)24:2<125::AID-EAT2>3.0.CO;2-G",
                    "doi_r": "10.2000/later",
                },
                "candidates": [{
                    "rank": 1,
                    "cosine_similarity": 0.9,
                    "corpus_index": 0,
                    "record_id": "candidate",
                }],
            }],
        }), encoding="utf-8")
        audit.write_text(json.dumps({"records": [
            {
                "doi_o": "10.1002/(sici)1098-108x(199809)24:2<125::aid-eat2>3.0.co;2-g",
                "doi_r": "10.2000/later",
                "combined_classification": "no_exact_doi_or_title_match",
            },
            {
                "doi_o": "10.3/already",
                "doi_r": "10.4/already",
                "combined_classification": "same_pair_recorded",
            },
        ]}), encoding="utf-8")
        return rankings, audit

    def test_maps_legacy_doi_and_expands_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rankings, audit = self._files(root)
            payload = build_queue(rankings, audit, top_k=1)
            self.assertEqual(payload["counts"]["audit_rows_not_already_same_pair"], 1)
            self.assertEqual(payload["counts"]["mapped_queue_records"], 1)
            self.assertEqual(payload["counts"]["unmapped_audit_records"], 0)
            self.assertEqual(payload["records"][0]["candidates"][0]["record"]["id"], "candidate")
            self.assertEqual(len(payload["inputs"]["rankings"]["sha256"]), 64)

            output = root / "queue.json"
            write_queue(payload, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

    def test_reports_unmapped_rows_instead_of_dropping_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rankings, audit = self._files(root)
            data = json.loads(audit.read_text(encoding="utf-8"))
            data["records"][0]["doi_r"] = "10.2000/not-ranked"
            audit.write_text(json.dumps(data), encoding="utf-8")
            payload = build_queue(rankings, audit)
            self.assertEqual(payload["counts"]["mapped_queue_records"], 0)
            self.assertEqual(payload["counts"]["unmapped_audit_records"], 1)
            self.assertEqual(payload["unmapped_audit_records"][0]["doi_r"], "10.2000/not-ranked")


if __name__ == "__main__":
    unittest.main()
