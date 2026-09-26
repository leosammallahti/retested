from __future__ import annotations

import unittest
import sys
import tempfile
import types
import importlib.metadata
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pipeline.pair_embeddings import (
    RankedCandidate,
    _embed,
    _fingerprint,
    _match_text,
    _records,
    build_output,
    rank_top_k,
    split_records,
)


class PairEmbeddingTests(unittest.TestCase):
    def test_match_summary_is_the_embedding_text(self):
        self.assertEqual(
            _match_text({"match_summary": "Two short sentences.", "identity_text": "A much longer record."}),
            "What was tested: Two short sentences.",
        )

    def test_embedding_text_includes_title_anchors_but_not_result(self):
        record = {
            "match_summary": "The original effect was retested.",
            "observed_result": "It failed.",
            "components": {
                "original_title": [{"text": "Original title"}],
                "replication_title": [{"text": "Later title"}],
            },
        }
        text = _match_text(record)
        self.assertIn("Original paper: Original title", text)
        self.assertIn("Later paper: Later title", text)
        self.assertNotIn("failed", text)

    def test_textless_corpus_records_are_preserved_but_not_ranked(self):
        query = {"record_id": "q", "dataset": "retested", "match_summary": "query"}
        textless = {"record_id": "empty", "dataset": "forrt", "match_summary": None, "identity_text": None}
        candidate = {"record_id": "hit", "dataset": "forrt", "match_summary": "candidate"}
        output = build_output(
            [query, textless, candidate],
            [[RankedCandidate(index=0, score=0.9, boundary_tie_count=3, boundary_tie_selected=1)]],
            [query],
            [textless, candidate],
            model="test",
            query_fingerprint="q",
            corpus_fingerprint="c",
            top_k=1,
            input_path=Path("input.json"),
            embedded_corpus_indexes=[1],
        )
        self.assertEqual(output["counts"]["forrt_records"], 2)
        self.assertEqual(output["counts"]["forrt_records_without_text"], 1)
        self.assertEqual(output["textless_corpus_record_ids"], ["empty"])
        self.assertEqual(output["queries"][0]["candidates"][0]["corpus_index"], 1)
        self.assertIsNone(output["corpus_records"][0]["embedding_text_sha256"])
        self.assertEqual(len(output["corpus_records"][1]["embedding_text_sha256"]), 64)
        self.assertEqual(output["queries"][0]["boundary_tie"], {
            "cosine_similarity": 0.9,
            "corpus_records_at_score": 3,
            "selected_at_score": 1,
            "truncated": True,
        })

    def test_reads_query_and_corpus_schema(self):
        records = _records({
            "query_records": [{"record_id": "q", "identity_text": "query"}],
            "corpus_records": [{"record_id": "c", "identity_text": "candidate"}],
        })
        self.assertEqual([record["dataset"] for record in records], ["retested", "forrt"])

    def test_split_records_accepts_only_explicit_sides(self):
        queries, corpus = split_records([
            {"dataset": "retested", "identity_text": "query"},
            {"dataset": "forrt", "identity_text": "candidate"},
            {"dataset": "other", "identity_text": "ignored"},
        ])
        self.assertEqual([record["identity_text"] for record in queries], ["query"])
        self.assertEqual([record["identity_text"] for record in corpus], ["candidate"])

    def test_rank_top_k_returns_descending_cosine(self):
        queries = np.asarray([[1.0, 0.0]], dtype=np.float32)
        corpus = np.asarray([[0.0, 1.0], [0.8, 0.6], [1.0, 0.0]], dtype=np.float32)
        ranked = rank_top_k(queries, corpus, 2)[0]
        self.assertEqual([candidate.index for candidate in ranked], [2, 1])
        self.assertAlmostEqual(ranked[0].score, 1.0)
        self.assertAlmostEqual(ranked[1].score, 0.8)

    def test_rank_top_k_breaks_boundary_ties_by_record_id(self):
        queries = np.asarray([[1.0, 0.0]], dtype=np.float32)
        corpus = np.asarray([[1.0, 0.0]] * 4, dtype=np.float32)
        ranked = rank_top_k(queries, corpus, 2, corpus_ids=["z", "a", "c", "b"])[0]
        self.assertEqual([candidate.index for candidate in ranked], [1, 3])
        self.assertEqual(ranked[-1].boundary_tie_count, 4)
        self.assertEqual(ranked[-1].boundary_tie_selected, 2)

    def test_rank_rejects_invalid_k(self):
        with self.assertRaises(ValueError):
            rank_top_k(np.ones((1, 2)), np.ones((1, 2)), 2)

    def test_invalid_embedding_cache_is_recomputed(self):
        class FakeTextEmbedding:
            def __init__(self, **_kwargs):
                pass

            def embed(self, texts, **_kwargs):
                return iter(np.asarray([1.0, float(index + 1)], dtype=np.float32) for index, _ in enumerate(texts))

            query_embed = embed

        texts = ["one", "two"]
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            fingerprint = _fingerprint("fake", texts, "corpus")
            np.save(cache / f"{fingerprint}.npy", np.asarray([[float("nan")]], dtype=np.float64))
            fake_module = types.SimpleNamespace(TextEmbedding=FakeTextEmbedding)
            with patch.dict(sys.modules, {"fastembed": fake_module}):
                vectors, returned = _embed(texts, "fake", "corpus", cache, batch_size=2, threads=1)
        self.assertEqual(returned, fingerprint)
        self.assertEqual(vectors.shape, (2, 2))
        self.assertTrue(np.isfinite(vectors).all())
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), np.ones(2), rtol=1e-6)

    def test_per_text_cache_only_embeds_changed_text(self):
        calls = []

        class FakeTextEmbedding:
            def __init__(self, **_kwargs):
                pass

            def embed(self, texts, **_kwargs):
                items = list(texts)
                calls.append(items)
                return iter(
                    np.asarray([len(item), index + 1.0], dtype=np.float32)
                    for index, item in enumerate(items)
                )

            query_embed = embed

        fake_module = types.SimpleNamespace(TextEmbedding=FakeTextEmbedding)
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, {"fastembed": fake_module}), patch.object(
            importlib.metadata, "version", return_value="test"
        ):
            cache = Path(folder)
            _embed(["one", "two"], "fake", "corpus", cache, batch_size=2, threads=1)
            _embed(["one", "three"], "fake", "corpus", cache, batch_size=2, threads=1)

        self.assertEqual(calls, [["one", "two"], ["three"]])


if __name__ == "__main__":
    unittest.main()
