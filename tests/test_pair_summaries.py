"""Focused checks for deterministic pair-match summary records."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.pair_summaries import (
    FORRT_ROOT,
    SourceBatch,
    build_document,
    canonical_dois,
    load_csv_batches,
    write_document,
)


def promoted_row(**changes) -> dict:
    row = {
        "doi_o": "10.1234/original",
        "doi_r": "10.5678/later",
        "effect_claim": "Warm objects make unfamiliar people seem friendlier.",
        "effect_claim_quote": "Targets were judged friendlier after participants held the warm object.",
        "replication_target_quote": "We tested the warm-object impression effect.",
        "original_title": "Experiencing physical warmth promotes interpersonal warmth",
        "replication_title": "A new test of physical warmth",
        "outcome": "failed",
        "outcome_quote": "The warm and cold conditions did not differ in friendliness ratings.",
    }
    row.update(changes)
    return row


class PairSummaryTests(unittest.TestCase):
    def test_every_default_raw_batch_is_manifest_declared_comparison_input(self):
        manifest = json.loads((FORRT_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
        declared = set(manifest["comparison_inputs"])
        actual = {
            batch.path.removeprefix("data/raw/forrt/")
            for batch in load_csv_batches()
        }
        actual.update({
            "fred-data/output_FReD.xlsx",
            "osf/version-history/FReD_2.4.1_2025-06-25.xlsx",
        })
        self.assertEqual(actual, declared)
        entries = {entry["path"]: entry for entry in manifest["files"]}
        self.assertTrue(all(path in entries for path in declared))
        self.assertTrue(all(entries[path].get("sha256") for path in declared))
        self.assertTrue(all(str(entries[path].get("source_url", "")).startswith("http") for path in declared))

    def test_groups_canonical_query_pairs_and_keeps_result_separate(self):
        # These are two curated rows but one canonical pair after FORRT's
        # doubled-slash DOI spelling is folded.
        promoted = [
            promoted_row(doi_o="10.1234//original"),
            promoted_row(
                effect_claim="Holding a warm object increases friendly impressions of a stranger.",
                outcome_quote="No friendly-impression advantage appeared for the warm condition.",
            ),
        ]
        extractor = SourceBatch(
            source="extractor",
            status="extractor",
            path="extractor.csv",
            rows=[{
                "doi_o": "10.1234/original",
                "doi_r": "10.5678/later",
                "title_o": "Experiencing physical warmth promotes interpersonal warmth",
                "title_r": "A new test of physical warmth",
                "abstract_r": "A new participant sample completed the temperature task.",
                "outcome": "successful",
                "outcome_phrase": "The warm condition produced higher friendliness ratings.",
            }],
        )
        validated = SourceBatch(
            source="validation",
            status="validated",
            path="validated.csv",
            rows=[{
                "doi_o": "10.1234/original",
                "doi_r": "10.5678/later",
                "description": "Physical warmth changes impressions of another person.",
                "outcome": "failed",
                "outcome_quote": "The validated record reports no condition difference.",
            }],
        )

        document = build_document(promoted, [extractor, validated])

        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(len(document["query_records"]), 1)
        self.assertIsNone(document["sources"][0]["sha256"])
        query = document["query_records"][0]
        self.assertEqual((query["doi_o"], query["doi_r"]), ("10.1234/original", "10.5678/later"))
        self.assertEqual(len(query["provenance"]), 2)
        self.assertEqual(len(query["components"]["effect_claim"]), 2)
        self.assertEqual(query["observed_result"], promoted[0]["outcome_quote"])
        self.assertNotIn(promoted[0]["outcome_quote"], query["identity_text"])
        self.assertEqual(
            query["match_summary"],
            "Warm objects make unfamiliar people seem friendlier. We tested the warm-object impression effect.",
        )
        self.assertNotIn(query["observed_result"], query["match_summary"])
        self.assertEqual(
            [item["component"] for item in query["match_summary_components"]],
            ["effect_claim", "replication_target"],
        )

        self.assertEqual(len(document["corpus_records"]), 1)
        corpus = document["corpus_records"][0]
        self.assertEqual(query["exact_corpus_record_id"], corpus["record_id"])
        self.assertEqual(len(corpus["provenance"]), 2)
        self.assertEqual(corpus["observed_result"], "The validated record reports no condition difference.")
        self.assertNotIn(corpus["observed_result"], corpus["identity_text"])
        self.assertNotIn(corpus["observed_result"], corpus["match_summary"])
        self.assertEqual(len(corpus["match_summary_components"]), 2)
        description = corpus["components"]["description"][0]
        self.assertEqual(description["text"], "Physical warmth changes impressions of another person.")
        self.assertEqual(len(description["provenance_ids"]), 1)
        self.assertIn("original_abstract", corpus["missing_components"])

    def test_includes_title_keyed_pairs_and_unresolved_pending_papers(self):
        public = SourceBatch(
            source="flora_public",
            status="published",
            path="flora.csv",
            rows=[
                {
                    "title_o": "An original effect without a DOI",
                    "title_r": "A public replication without a DOI",
                    "outcome": "mixed",
                    "outcome_quote": "One test agreed and another did not.",
                },
                {
                    "doi_o": "10.1000/unmatched-original",
                    "doi_r": "10.1000/unmatched-later",
                    "title_o": "An unmatched original",
                    "title_r": "An unmatched replication",
                },
            ],
        )
        pending = SourceBatch(
            source="extractor_pending",
            status="pending_original_unresolved",
            path="target_pending.csv",
            rows=[{
                "title_r": "A replication whose original is unresolved. A subtitle that must not add a third sentence",
                "abstract_r": "The paper reports a new test of a previously published claim.",
                "outcome": "pending",
            }],
        )

        document = build_document([promoted_row()], [public, pending])
        corpus = document["corpus_records"]

        self.assertEqual(len(corpus), 3)
        title_pair = next(record for record in corpus if record["record_kind"] == "pair" and record["doi_o"] is None)
        self.assertTrue(title_pair["original_key"].startswith("title-sha256:"))
        self.assertTrue(title_pair["replication_key"].startswith("title-sha256:"))
        self.assertIsNone(title_pair["doi_r"])

        unresolved = next(record for record in corpus if record["record_kind"] == "later_paper_status")
        self.assertIsNone(unresolved["original_key"])
        self.assertIn("original_identity", unresolved["missing_components"])
        self.assertIn("original_title", unresolved["missing_components"])
        self.assertEqual(unresolved["provenance"][0]["status"], "pending_original_unresolved")
        self.assertIn("previously published claim", unresolved["identity_text"])
        self.assertNotIn("subtitle", unresolved["match_summary"].casefold())

        unmatched = next(record for record in corpus if record["doi_r"] == "10.1000/unmatched-later")
        self.assertIsNone(document["query_records"][0]["exact_corpus_record_id"])
        self.assertEqual(unmatched["record_kind"], "pair")

    def test_multiple_identifiers_and_json_output_are_stable(self):
        self.assertEqual(
            canonical_dois("https://doi.org/10.1234//ONE; DOI:10.5678/TWO&amp;"),
            ("10.1234/one", "10.5678/two"),
        )
        self.assertEqual(
            canonical_dois("https://doi.org/10.1002/(SICI)1098-108X(199809)24:2%3C125::AID-EAT2%3E3.0.CO;2-G"),
            ("10.1002/(sici)1098-108x(199809)24:2<125::aid-eat2>3.0.co;2-g",),
        )
        source = SourceBatch(
            source="versions",
            status="validated",
            path="versions.csv",
            rows=[{
                "doi_o": "10.1000/original",
                "doi_r": "10.1000/preprint",
                "doi_r_published": "10.1000/article",
                "title_o": "Original",
                "title_r": "Later report",
            }],
        )
        document = build_document([], [source])
        self.assertEqual({record["doi_r"] for record in document["corpus_records"]}, {
            "10.1000/article",
            "10.1000/preprint",
        })
        for record in document["corpus_records"]:
            self.assertEqual(
                {item["value"] for item in record["identifiers"]["replication"]},
                {"10.1000/article", "10.1000/preprint"},
            )

        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.json"
            second = Path(folder) / "second.json"
            write_document(document, first)
            write_document(document, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text(encoding="utf-8")), document)

    def test_local_loader_excludes_literature_search_results(self):
        header = "doi_o,doi_r,title_o,title_r\n"
        row = "10.1000/original,10.1000/later,Original,Later\n"
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            allowed = root / "fred-data" / "output_flora.csv"
            excluded = root / "repos" / "fred-litsearch" / "openalex_results_10000.csv"
            allowed.parent.mkdir(parents=True)
            excluded.parent.mkdir(parents=True)
            allowed.write_text(header + row, encoding="utf-8")
            excluded.write_text(header + row, encoding="utf-8")

            batches = load_csv_batches(root)

        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].status, "published")
        self.assertTrue(batches[0].path.endswith("fred-data/output_flora.csv"))
        self.assertEqual(len(batches[0].sha256), 64)


if __name__ == "__main__":
    unittest.main()
