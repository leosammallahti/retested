"""Retrieve possible FORRT matches for Retested pairs from standardized summaries.

The embeddings are deliberately a retrieval aid, not an identity decision.  The
output retains the nearest candidates for source review; it never labels a pair
as present or absent on cosine similarity alone.

Run after ``python -m pipeline.pair_summaries``::

    python -m pipeline.pair_embeddings --top-k 20

Install the optional local embedding dependency with
``pip install -e '.[matching]'``.  Model files and numeric arrays live under
``data/cache`` and are not build inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from .load import ROOT

DEFAULT_INPUT = ROOT / "data" / "discovery" / "pair_match_summaries.json"
DEFAULT_OUTPUT = ROOT / "data" / "discovery" / "pair_match_candidates.json"
DEFAULT_CACHE = ROOT / "data" / "cache" / "pair-matching"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_PIPELINE_VERSION = 2
TEXT_CACHE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RankedCandidate:
    index: int
    score: float
    boundary_tie_count: int = 1
    boundary_tie_selected: int = 1


def _records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("query_records"), list) and isinstance(payload.get("corpus_records"), list):
            records = [
                *({**record, "dataset": "retested"} for record in payload["query_records"]),
                *({**record, "dataset": "forrt"} for record in payload["corpus_records"]),
            ]
        else:
            records = payload.get("records")
    else:
        records = None
    if not isinstance(records, list):
        raise ValueError("summary file must be a list or an object containing a records list")
    for number, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {number} is not an object")
    return records


def _side(record: dict) -> str:
    # ``dataset`` is the preferred field; the fallbacks keep the retriever usable
    # with early scratch exports without weakening validation of the text itself.
    return str(record.get("dataset") or record.get("side") or record.get("source_group") or "").lower()


def _match_text(record: dict) -> str:
    """Two-sentence TLDR plus paper-title anchors, with no outcome text."""
    parts: list[str] = []
    components = record.get("components")
    if isinstance(components, dict):
        for label, name in (("Original paper", "original_title"), ("Later paper", "replication_title")):
            values = components.get(name)
            if isinstance(values, list) and values and isinstance(values[0], dict):
                value = str(values[0].get("text") or "").strip()
                if value:
                    parts.append(f"{label}: {value}")
    summary = str(record.get("match_summary") or record.get("identity_text") or "").strip()
    if summary:
        parts.append(f"What was tested: {summary}")
    return "\n".join(parts)


def split_records(records: Iterable[dict]) -> tuple[list[dict], list[dict]]:
    queries, corpus = [], []
    for record in records:
        side = _side(record)
        if side == "retested":
            queries.append(record)
        elif side in {"forrt", "flora", "fred"}:
            corpus.append(record)
    if not queries:
        raise ValueError("summary file contains no Retested query records")
    if not corpus:
        raise ValueError("summary file contains no FORRT corpus records")
    return queries, corpus


def rank_top_k(
    query_vectors: np.ndarray,
    corpus_vectors: np.ndarray,
    top_k: int,
    *,
    corpus_ids: Sequence[str] | None = None,
) -> list[list[RankedCandidate]]:
    """Return cosine candidates, breaking exact-score ties by corpus id."""
    if query_vectors.ndim != 2 or corpus_vectors.ndim != 2:
        raise ValueError("embedding matrices must be two-dimensional")
    if query_vectors.shape[1] != corpus_vectors.shape[1]:
        raise ValueError("query and corpus embedding dimensions differ")
    if not 1 <= top_k <= len(corpus_vectors):
        raise ValueError("top_k must be between one and the corpus size")
    if not np.isfinite(query_vectors).all() or not np.isfinite(corpus_vectors).all():
        raise ValueError("embedding matrices must contain only finite values")
    if corpus_ids is not None and len(corpus_ids) != len(corpus_vectors):
        raise ValueError("corpus_ids length must match the corpus size")

    # Numeric priorities make per-query tie handling cheap. Corpus index is the
    # tertiary key in case a scratch input supplies duplicate record ids.
    lexical_order = (
        sorted(range(len(corpus_vectors)), key=lambda index: (str(corpus_ids[index]), index))
        if corpus_ids is not None else list(range(len(corpus_vectors)))
    )
    tie_priority = np.empty(len(corpus_vectors), dtype=np.int64)
    tie_priority[lexical_order] = np.arange(len(corpus_vectors), dtype=np.int64)

    scores = query_vectors @ corpus_vectors.T
    if not np.isfinite(scores).all():
        raise ValueError("cosine score matrix contains non-finite values")
    results: list[list[RankedCandidate]] = []
    for row in scores:
        threshold = np.partition(row, len(row) - top_k)[len(row) - top_k]
        above = np.flatnonzero(row > threshold)
        boundary = np.flatnonzero(row == threshold)
        boundary_selected = top_k - len(above)
        boundary_order = boundary[np.argsort(tie_priority[boundary], kind="stable")]
        indexes = np.concatenate((above, boundary_order[:boundary_selected]))
        indexes = indexes[np.lexsort((tie_priority[indexes], -row[indexes]))]
        results.append([
            RankedCandidate(
                int(index),
                float(row[index]),
                boundary_tie_count=len(boundary) if row[index] == threshold else 1,
                boundary_tie_selected=boundary_selected if row[index] == threshold else 1,
            )
            for index in indexes
        ])
    return results


def _package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _fingerprint(model: str, texts: list[str], kind: str) -> str:
    digest = hashlib.sha256()
    digest.update(
        f"pair-match-v{EMBEDDING_PIPELINE_VERSION}\0{model}\0fastembed={_package_version('fastembed')}\0{kind}\0".encode()
    )
    for text in texts:
        digest.update(text.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _text_fingerprint(model: str, text: str, kind: str) -> str:
    raw = (
        f"pair-match-text-v{TEXT_CACHE_SCHEMA_VERSION}\0"
        f"{model}\0fastembed={_package_version('fastembed')}\0{kind}\0{text}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_vector(vector: np.ndarray) -> bool:
    return (
        vector.ndim == 1
        and vector.size > 0
        and np.issubdtype(vector.dtype, np.floating)
        and np.isfinite(vector).all()
        and float(np.linalg.norm(vector)) > 0
    )


def _load_text_vectors(cache_dir: Path, keys: Sequence[str]) -> dict[str, np.ndarray]:
    """Load valid individual vectors so a small corpus edit stays cheap."""
    if not keys:
        return {}
    cache_dir.mkdir(parents=True, exist_ok=True)
    database = cache_dir / "text-vectors.sqlite3"
    found: dict[str, np.ndarray] = {}
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS vectors "
            "(cache_key TEXT PRIMARY KEY, dimension INTEGER NOT NULL, vector BLOB NOT NULL)"
        )
        unique = list(dict.fromkeys(keys))
        for offset in range(0, len(unique), 500):
            chunk = unique[offset:offset + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = connection.execute(
                f"SELECT cache_key, dimension, vector FROM vectors WHERE cache_key IN ({placeholders})",
                chunk,
            )
            for key, dimension, blob in rows:
                vector = np.frombuffer(blob, dtype="<f4").copy()
                if vector.size == dimension and _valid_vector(vector):
                    found[key] = vector
    return found


def _store_text_vectors(cache_dir: Path, values: Mapping[str, np.ndarray]) -> None:
    if not values:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    database = cache_dir / "text-vectors.sqlite3"
    rows = []
    for key, value in values.items():
        vector = np.asarray(value, dtype="<f4")
        if _valid_vector(vector):
            rows.append((key, vector.size, sqlite3.Binary(vector.tobytes())))
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS vectors "
            "(cache_key TEXT PRIMARY KEY, dimension INTEGER NOT NULL, vector BLOB NOT NULL)"
        )
        connection.executemany(
            "INSERT OR REPLACE INTO vectors(cache_key, dimension, vector) VALUES (?, ?, ?)",
            rows,
        )


def _normalize_vectors(vectors: np.ndarray, expected_rows: int) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != expected_rows or not np.isfinite(vectors).all():
        raise ValueError("embedding model returned an invalid matrix")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms <= 0):
        raise ValueError("embedding model returned a zero-length vector")
    return vectors / norms


def _embed(texts: list[str], model_name: str, kind: str, cache_dir: Path, batch_size: int, threads: int) -> tuple[np.ndarray, str]:
    fingerprint = _fingerprint(model_name, texts, kind)
    vectors_path = cache_dir / f"{fingerprint}.npy"
    text_keys = [_text_fingerprint(model_name, item, kind) for item in texts]
    if vectors_path.exists():
        try:
            cached = np.load(vectors_path, allow_pickle=False)
            valid = (
                cached.ndim == 2
                and cached.shape[0] == len(texts)
                and cached.shape[1] > 0
                and np.issubdtype(cached.dtype, np.floating)
                and np.isfinite(cached).all()
                and np.all(np.linalg.norm(cached, axis=1) > 0)
            )
        except (OSError, ValueError):
            valid = False
        if valid:
            cached = np.asarray(cached, dtype=np.float32)
            _store_text_vectors(cache_dir, dict(zip(text_keys, cached, strict=True)))
            return cached, fingerprint
        vectors_path.unlink(missing_ok=True)

    by_key = _load_text_vectors(cache_dir, text_keys)
    if by_key:
        # Corrupt rows with a different dimension cannot be combined.  Retain
        # the modal dimension and let the model replace the outliers below.
        dimensions: dict[int, int] = {}
        for vector in by_key.values():
            dimensions[vector.size] = dimensions.get(vector.size, 0) + 1
        expected_dimension = max(dimensions, key=lambda dimension: (dimensions[dimension], dimension))
        by_key = {key: vector for key, vector in by_key.items() if vector.size == expected_dimension}

    missing: dict[str, str] = {}
    for key, item in zip(text_keys, texts, strict=True):
        if key not in by_key:
            missing.setdefault(key, item)
    new_by_key: dict[str, np.ndarray] = {}
    if missing:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise SystemExit("pair embeddings require the optional dependency: pip install -e '.[matching]'") from exc
        model_cache = cache_dir / "models"
        model = TextEmbedding(model_name=model_name, cache_dir=str(model_cache), threads=threads)
        method = model.query_embed if kind == "query" else model.embed
        missing_keys = list(missing)
        generated = _normalize_vectors(
            np.asarray(list(method([missing[key] for key in missing_keys], batch_size=batch_size))),
            len(missing_keys),
        )
        if by_key and generated.shape[1] != next(iter(by_key.values())).size:
            # The per-text cache belongs to an incompatible model response even
            # though its package/model fingerprint matched. Recompute all text.
            missing = dict(zip(text_keys, texts, strict=True))
            missing_keys = list(missing)
            generated = _normalize_vectors(
                np.asarray(list(method([missing[key] for key in missing_keys], batch_size=batch_size))),
                len(missing_keys),
            )
            by_key = {}
        new_by_key = dict(zip(missing_keys, generated, strict=True))
        _store_text_vectors(cache_dir, new_by_key)
        by_key.update(new_by_key)

    vectors = np.vstack([by_key[key] for key in text_keys]).astype(np.float32, copy=False)
    vectors = _normalize_vectors(vectors, len(texts))
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(vectors_path, vectors)
    return vectors, fingerprint


def _record_id(record: dict, fallback: str) -> str:
    return str(record.get("id") or record.get("record_id") or record.get("pair_id") or fallback)


def _brief(record: dict, fallback: str) -> dict:
    keep = (
        "doi_o", "doi_r", "title_o", "title_r", "original_title", "replication_title",
        "effect_name", "match_summary", "identity_text", "observed_result", "source_status", "sources", "provenance",
        "missing_components", "exact_corpus_record_id", "record_kind", "original_key",
        "replication_key", "identifiers", "status",
    )
    brief = {"id": _record_id(record, fallback), **{key: record[key] for key in keep if key in record}}
    components = record.get("components")
    if isinstance(components, dict):
        for output_name, component_name in (("original_title", "original_title"), ("replication_title", "replication_title")):
            values = components.get(component_name)
            if isinstance(values, list) and values and isinstance(values[0], dict) and values[0].get("text"):
                brief.setdefault(output_name, values[0]["text"])
    match_text = _match_text(record)
    brief["embedding_text_sha256"] = hashlib.sha256(match_text.encode("utf-8")).hexdigest() if match_text else None
    return brief


def build_output(records: list[dict], rankings: list[list[RankedCandidate]], queries: list[dict], corpus: list[dict],
                 *, model: str, query_fingerprint: str, corpus_fingerprint: str, top_k: int,
                 input_path: Path, embedded_corpus_indexes: list[int]) -> dict:
    query_rows = []
    corpus_rows = [_brief(record, f"forrt:{number}") for number, record in enumerate(corpus)]
    for query_number, (query, candidates) in enumerate(zip(queries, rankings, strict=True)):
        resolved = [(candidate, embedded_corpus_indexes[candidate.index]) for candidate in candidates]
        query_row = {
            "query": _brief(query, f"retested:{query_number}"),
            "candidates": [
                {"rank": rank, "cosine_similarity": round(candidate.score, 8),
                 "corpus_index": corpus_index,
                 "record_id": corpus_rows[corpus_index]["id"]}
                for rank, (candidate, corpus_index) in enumerate(resolved, 1)
            ],
        }
        if candidates and candidates[-1].boundary_tie_count > 1:
            last = candidates[-1]
            query_row["boundary_tie"] = {
                "cosine_similarity": round(last.score, 8),
                "corpus_records_at_score": last.boundary_tie_count,
                "selected_at_score": last.boundary_tie_selected,
                "truncated": last.boundary_tie_count > last.boundary_tie_selected,
            }
        query_rows.append(query_row)
    textless = [corpus_rows[index]["id"] for index, record in enumerate(corpus) if not _match_text(record)]
    return {
        "schema_version": 1,
        "purpose": "candidate retrieval only; similarity is not evidence that two pairs are identical or absent",
        "input": str(input_path),
        "model": model,
        "embedding_runtime": {"fastembed": _package_version("fastembed"), "pipeline_version": EMBEDDING_PIPELINE_VERSION},
        "top_k": top_k,
        "tie_breaker": "cosine_similarity_desc_then_record_id_asc",
        "counts": {
            "all_summary_records": len(records),
            "retested_queries": len(queries),
            "forrt_records": len(corpus),
            "forrt_records_embedded": len(embedded_corpus_indexes),
            "forrt_records_without_text": len(textless),
        },
        "embedding_fingerprints": {"queries": query_fingerprint, "corpus": corpus_fingerprint},
        "textless_corpus_record_ids": textless,
        "corpus_records": corpus_rows,
        "queries": query_rows,
    }


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT, *, model: str = DEFAULT_MODEL,
        top_k: int = 20, cache_dir: Path = DEFAULT_CACHE, batch_size: int = 128, threads: int = 4) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = _records(payload)
    queries, corpus = split_records(records)
    textless_queries = [_record_id(record, str(number)) for number, record in enumerate(queries) if not _match_text(record)]
    if textless_queries:
        raise ValueError(f"Retested query records lack match text: {', '.join(textless_queries[:10])}")
    embedded_corpus_indexes = [index for index, record in enumerate(corpus) if _match_text(record)]
    if not embedded_corpus_indexes:
        raise ValueError("FORRT corpus contains no records with match text")
    query_texts = [_match_text(record) for record in queries]
    corpus_texts = [_match_text(corpus[index]) for index in embedded_corpus_indexes]
    if top_k > len(corpus_texts):
        raise ValueError(f"top_k {top_k} exceeds embedded FORRT corpus size {len(corpus_texts)}")
    query_vectors, query_fingerprint = _embed(query_texts, model, "query", cache_dir, batch_size, threads)
    corpus_vectors, corpus_fingerprint = _embed(corpus_texts, model, "corpus", cache_dir, batch_size, threads)
    embedded_corpus_ids = [
        _record_id(corpus[index], f"forrt:{index}")
        for index in embedded_corpus_indexes
    ]
    rankings = rank_top_k(query_vectors, corpus_vectors, top_k, corpus_ids=embedded_corpus_ids)
    output = build_output(records, rankings, queries, corpus, model=model, query_fingerprint=query_fingerprint,
                          corpus_fingerprint=corpus_fingerprint, top_k=top_k, input_path=input_path,
                          embedded_corpus_indexes=embedded_corpus_indexes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args(argv)
    output = run(args.input, args.output, model=args.model, top_k=args.top_k, cache_dir=args.cache_dir,
                 batch_size=args.batch_size, threads=args.threads)
    print(json.dumps(output["counts"], indent=2))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
