"""Tests for the dependency-free paper/pair retrieval benchmark."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.pair_match_benchmark import (
    evaluate,
    load_embedded_truth,
    load_rankings,
    load_repository_truth,
    normalize_truth_rows,
    query_id_for_pair,
)


class PairMatchBenchmarkTests(unittest.TestCase):
    def test_paper_and_pair_hits_have_separate_denominators(self) -> None:
        truth = normalize_truth_rows([
            {
                "query_id": "alias-pair",
                "doi_o": "10.1000/original-a",
                "doi_r": "10.1000/journal-a",
                "gold_paper_ids": ["10.1000/journal-a", "10.31234/osf.io/preprint-a"],
                "strata": {"match_basis": "alternate_doi"},
            },
            {
                "query_id": "paper-only",
                "doi_r": "10.1000/later-b",
                "gold_pairs": [],
                "strata": ["relation=later_paper_only"],
            },
            {
                "query_id": "missing-ranking",
                "doi_o": "10.1000/original-c",
                "doi_r": "10.1000/later-c",
                "strata": ["match_basis=exact_doi"],
            },
        ])
        rankings = {
            "alias-pair": {
                "candidates": [
                    {"doi_o": "10.1000/wrong", "doi_r": "10.1000/wrong-paper"},
                    {"doi_o": "10.1000/original-a", "doi_r": "10.31234/osf.io/preprint-a"},
                ],
                "strata": [],
            },
            "paper-only": {
                "candidates": [{"doi_r": "10.1000/later-b"}],
                "strata": [],
            },
        }

        result = evaluate(rankings, truth, ks=(1, 3, 5, 10, 20, 50))

        paper = result["overall"]["paper"]
        pair = result["overall"]["pair"]
        self.assertEqual(paper["queries"], 3)
        self.assertEqual(paper["hit_at"]["1"], {"hits": 1, "total": 3, "rate": 0.333333})
        self.assertEqual(paper["hit_at"]["3"], {"hits": 2, "total": 3, "rate": 0.666667})
        self.assertEqual(pair["queries"], 2)
        self.assertEqual(pair["hit_at"]["1"]["hits"], 0)
        self.assertEqual(pair["hit_at"]["3"]["hits"], 1)
        self.assertEqual(result["overall"]["paper_miss_query_ids_at_max_k"], ["missing-ranking"])
        self.assertEqual(result["overall"]["pair_miss_query_ids_at_max_k"], ["missing-ranking"])
        self.assertEqual(result["by_stratum"]["match_basis=alternate_doi"]["paper"]["hit_at"]["3"]["rate"], 1.0)
        self.assertEqual(result["by_stratum"]["relation=later_paper_only"]["pair"]["queries"], 0)

    def test_pair_rank_requires_the_correct_original(self) -> None:
        truth = normalize_truth_rows([{
            "query_id": "q",
            "doi_o": "10.1000/original",
            "doi_r": "10.1000/later",
        }])
        rankings = {
            "q": {
                "candidates": [
                    {"doi_o": "10.1000/different-original", "doi_r": "10.1000/later"},
                    {"doi_o": "10.1000/original", "doi_r": "10.1000/later"},
                ],
                "strata": [],
            }
        }

        result = evaluate(rankings, truth, ks=(1, 3))

        self.assertEqual(result["overall"]["paper"]["hit_at"]["1"]["rate"], 1.0)
        self.assertEqual(result["overall"]["pair"]["hit_at"]["1"]["rate"], 0.0)
        self.assertEqual(result["overall"]["pair"]["hit_at"]["3"]["rate"], 1.0)

    def test_repository_truth_includes_overlays_aliases_and_paper_only_rows(self) -> None:
        attempts = {
            "overlay": {
                "doi_o": "10.1000/original-overlay",
                "doi_r": "10.1000/later-overlay",
                "sources": ["flora", "retested"],
                "retested_review": {"reviewed_on": "2026-09-26"},
            },
            "retested-only": {
                "doi_o": "10.1000/original-new",
                "doi_r": "10.1000/later-new",
                "sources": ["retested"],
                "retested_review": {"reviewed_on": "2026-09-26"},
            },
        }
        audit = {
            "records": [
                {
                    "doi_o": "10.1000/original-a",
                    "doi_r": "10.1000/journal-a",
                    "classification": "same_pair_title_alternate_doi",
                    "combined_classification": "same_pair_recorded",
                    "evidence": {"source_replication_dois": ["10.31234/osf.io/preprint-a"]},
                    "live_match": {
                        "match_basis": "title",
                        "source_later_dois": ["10.31234/osf.io/preprint-a"],
                    },
                },
                {
                    "doi_o": "10.1000/unconfirmed-original",
                    "doi_r": "10.1000/later-only",
                    "classification": "later_paper_doi_only",
                    "combined_classification": "later_paper_recorded_pair_unconfirmed",
                    "live_match": {"match_basis": "doi", "source_later_dois": ["10.1000/later-only"]},
                },
                {
                    "doi_o": "10.1000/absent-original",
                    "doi_r": "10.1000/absent-later",
                    "classification": "no_exact_doi_or_title_match_in_local_forrt_tables",
                    "combined_classification": "no_exact_doi_or_title_match",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as folder:
            attempts_path = Path(folder) / "attempts.json"
            audit_path = Path(folder) / "audit.json"
            attempts_path.write_text(json.dumps(attempts), encoding="utf-8")
            audit_path.write_text(json.dumps(audit), encoding="utf-8")
            truth = load_repository_truth(attempts_path, audit_path)

        overlay_key = query_id_for_pair("10.1000/original-overlay", "10.1000/later-overlay")
        alias_key = query_id_for_pair("10.1000/original-a", "10.1000/journal-a")
        paper_only_key = query_id_for_pair("10.1000/unconfirmed-original", "10.1000/later-only")
        self.assertEqual(len(truth), 3)
        self.assertIn(overlay_key, truth)
        self.assertEqual(
            truth[alias_key]["paper_ids"],
            frozenset({"10.1000/journal-a", "10.31234/osf.io/preprint-a"}),
        )
        self.assertTrue(truth[alias_key]["pairs"])
        self.assertFalse(truth[paper_only_key]["pairs"])
        self.assertIn("relation=later_paper_only", truth[paper_only_key]["strata"])

    def test_load_rankings_accepts_query_mapping(self) -> None:
        payload = {
            "q1": [{"doi_r": "10.1000/one"}],
            "q2": [{"doi_r": "10.1000/two"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rankings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rankings = load_rankings(path)
        self.assertEqual(set(rankings), {"q1", "q2"})
        self.assertEqual(rankings["q1"]["candidates"][0]["doi_r"], "10.1000/one")

    def test_accepts_pair_embeddings_nested_output(self) -> None:
        payload = {
            "schema_version": 1,
            "queries": [{
                "query": {
                    "id": "an-implementation-specific-id",
                    "doi_o": "10.1000/original",
                    "doi_r": "10.1000/later",
                },
                "candidates": [{
                    "rank": 1,
                    "cosine_similarity": 0.91,
                    "record": {"doi_o": "10.1000/original", "doi_r": "10.1000/later"},
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rankings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rankings = load_rankings(path)
        query_id = query_id_for_pair("10.1000/original", "10.1000/later")
        truth = normalize_truth_rows([{"doi_o": "10.1000/original", "doi_r": "10.1000/later"}])
        result = evaluate(rankings, truth, ks=(1,))
        self.assertIn(query_id, rankings)
        self.assertEqual(result["overall"]["paper"]["hit_at"]["1"]["rate"], 1.0)
        self.assertEqual(result["overall"]["pair"]["hit_at"]["1"]["rate"], 1.0)

    def test_resolves_top_level_corpus_references_and_embedded_truth(self) -> None:
        payload = {
            "corpus_records": [
                {
                    "id": "forrt:wrong",
                    "doi_o": "10.1000/wrong-original",
                    "doi_r": "10.1000/wrong-later",
                    "status": "same_pair",
                },
                {
                    "id": "forrt:gold",
                    "doi_o": "10.1000/original",
                    "doi_r": "10.1000/journal",
                    "replication_key": "doi:10.1000/journal",
                    "identifiers": {
                        "original": [{"kind": "doi", "value": "10.1000/original"}],
                        "replication": [
                            {"kind": "doi", "value": "10.1000/journal"},
                            {"kind": "doi", "value": "10.31234/osf.io/preprint"},
                        ],
                    },
                    "status": "same_pair",
                },
            ],
            "queries": [{
                "query": {
                    "doi_o": "10.1000/original",
                    "doi_r": "10.31234/osf.io/preprint",
                    "exact_corpus_record_id": "forrt:gold",
                },
                "candidates": [
                    {"rank": 1, "cosine_similarity": 0.92, "corpus_index": 0, "record_id": "forrt:wrong"},
                    {"rank": 2, "cosine_similarity": 0.90, "corpus_index": 1, "record_id": "forrt:gold"},
                ],
            }],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rankings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            rankings = load_rankings(path)
            truth = load_embedded_truth(path)
        result = evaluate(rankings, truth, ks=(1, 3))
        self.assertEqual(result["overall"]["paper"]["hit_at"]["1"]["rate"], 0.0)
        self.assertEqual(result["overall"]["paper"]["hit_at"]["3"]["rate"], 1.0)
        self.assertEqual(result["overall"]["pair"]["hit_at"]["3"]["rate"], 1.0)
        self.assertIn("source=embedded_exact", next(iter(truth.values()))["strata"])

    def test_embedded_truth_stratifies_textless_and_duplicate_gold_records(self) -> None:
        payload = {
            "corpus_records": [
                {
                    "id": "gold-with-text",
                    "doi_o": "10.1000/original-a",
                    "doi_r": "10.1000/later-a",
                    "match_summary": "Gold source-derived matching text.",
                    "embedding_text_sha256": "a" * 64,
                },
                {
                    "id": "same-text-other-pair",
                    "doi_o": "10.1000/original-b",
                    "doi_r": "10.1000/later-b",
                    "match_summary": "Different visible text with the same exact embedding input hash.",
                    "embedding_text_sha256": "a" * 64,
                },
                {
                    "id": "gold-without-text",
                    "doi_o": "10.1000/original-c",
                    "doi_r": "10.1000/later-c",
                    "match_summary": None,
                    "identity_text": None,
                },
            ],
            "queries": [
                {
                    "query": {
                        "doi_o": "10.1000/original-a",
                        "doi_r": "10.1000/later-a",
                        "exact_corpus_record_id": "gold-with-text",
                    },
                    "candidates": [],
                },
                {
                    "query": {
                        "doi_o": "10.1000/original-c",
                        "doi_r": "10.1000/later-c",
                        "exact_corpus_record_id": "gold-without-text",
                    },
                    "candidates": [],
                },
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rankings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            truth = load_embedded_truth(path)

        duplicate = truth[query_id_for_pair("10.1000/original-a", "10.1000/later-a")]["strata"]
        textless = truth[query_id_for_pair("10.1000/original-c", "10.1000/later-c")]["strata"]
        self.assertIn("semantic_retrieval_coverage=eligible", duplicate)
        self.assertIn("gold_match_text=duplicate", duplicate)
        self.assertIn("gold_match_text_multiplicity=2-5", duplicate)
        self.assertIn("semantic_retrieval_coverage=textless_gold", textless)
        self.assertIn("gold_match_text=missing", textless)


if __name__ == "__main__":
    unittest.main()
