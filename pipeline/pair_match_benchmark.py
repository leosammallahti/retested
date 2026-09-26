"""Evaluate precomputed FORRT paper and original/later-pair rankings.

The benchmark deliberately does not compute embeddings.  It consumes a ranked
candidate JSON file, so dense, lexical, hybrid, and hand-built retrieval systems
can be compared with the same evaluator.

Ranking JSON may be a list, ``{"queries": [...]}``, ``{"rankings": [...]}``, or
a mapping from query id to candidate lists.  Candidates can contain their paper
fields inline, under ``record``, or refer to a top-level ``corpus_records`` row
with ``corpus_index``/``record_id``.  The canonical query form is::

    {
      "query_id": "10.1000/original::10.1000/later",
      "candidates": [
        {
          "doi_o": "10.1000/candidate-original",
          "doi_r": "10.1000/candidate-later",
          "paper_ids": ["10.1000/candidate-later", "10.31234/osf.io/alias"]
        }
      ]
    }

By default truth is built from the repository's source-reviewed FORRT overlays
and overlap audit.  A custom truth JSON can instead be supplied with ``--truth``.
Truth rows accept ``gold_paper_ids`` (aliases for one later paper),
``gold_pairs`` (``doi_o``/``doi_r`` objects), and ``strata``.  A row containing
only ``doi_o`` and ``doi_r`` is treated as a known pair.  An explicit empty
``gold_pairs`` list makes it a paper-presence-only positive.

Every candidate object occupies one rank.  Retrieval producers should therefore
canonicalize and deduplicate paper versions before writing the rankings.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .ids import norm_doi
from .load import ROOT

DEFAULT_KS = (1, 3, 5, 10, 20, 50)
ATTEMPTS = ROOT / "data" / "build" / "attempts.json"
OVERLAP_AUDIT = ROOT / "data" / "curated" / "forrt_overlap_audit_20260926.json"


def normalize_identifier(value: Any) -> str | None:
    """Normalize a DOI when possible and otherwise a stable external id."""
    if value is None:
        return None
    doi = norm_doi(value)
    if doi:
        return re.sub(r"^(10\.\d{4,9})/+", r"\1/", doi)
    text = str(value).strip().casefold()
    if not text:
        return None
    for prefix in ("https://openalex.org/", "http://openalex.org/"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.rstrip("/") or None


def query_id_for_pair(doi_o: Any, doi_r: Any) -> str:
    """Return the query id used by repository-derived truth rows."""
    original = normalize_identifier(doi_o)
    later = normalize_identifier(doi_r)
    if not original or not later:
        raise ValueError("A pair query needs doi_o and doi_r")
    return f"{original}::{later}"


def _values(row: dict[str, Any], *keys: str) -> set[str]:
    out: set[str] = set()
    for key in keys:
        value = row.get(key)
        if isinstance(value, (list, tuple, set)):
            items = value
        elif value is None:
            items = ()
        else:
            items = (value,)
        out.update(identifier for item in items if (identifier := normalize_identifier(item)))
    return out


def _side_identifiers(row: dict[str, Any], side: str) -> set[str]:
    """Read canonical ids from summary-style ``keys``/``identifiers`` fields."""
    out: set[str] = set()
    key_name = "original_key" if side == "original" else "replication_key"
    out.update(_values(row, key_name))
    keys = row.get("keys")
    if isinstance(keys, dict):
        value = keys.get(side) or keys.get(key_name)
        holder = {"value": value}
        out.update(_values(holder, "value"))
    identifiers = row.get("identifiers")
    if isinstance(identifiers, dict) and isinstance(identifiers.get(side), list):
        for item in identifiers[side]:
            if isinstance(item, dict):
                out.update(_values(item, "value", "doi", "id"))
            else:
                out.update(_values({"value": item}, "value"))
    return out


def _strata(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {f"{key}={item}" for key, item in value.items() if item is not None and str(item).strip()}
    if isinstance(value, str):
        return {value} if value.strip() else set()
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value if item is not None and str(item).strip()}
    return set()


def _query_id(row: dict[str, Any]) -> str:
    query_id = row.get("query_id")
    if query_id is not None and str(query_id).strip():
        return str(query_id).strip()
    if row.get("doi_o") and row.get("doi_r"):
        return query_id_for_pair(row["doi_o"], row["doi_r"])
    query_id = row.get("id") or row.get("record_id") or row.get("pair_id")
    if query_id is not None and str(query_id).strip():
        return str(query_id).strip()
    if row.get("doi_r"):
        later = normalize_identifier(row["doi_r"])
        if later:
            return later
    raise ValueError("Each query needs query_id, or doi_o and doi_r")


def _unwrap_rows(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next((payload[key] for key in keys if isinstance(payload.get(key), list)), None)
        if rows is None and all(isinstance(value, list) for value in payload.values()):
            rows = [{"query_id": key, "candidates": value} for key, value in payload.items()]
        elif rows is None and all(isinstance(value, dict) for value in payload.values()):
            rows = [dict(value, query_id=value.get("query_id", key)) for key, value in payload.items()]
    else:
        rows = None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("JSON must contain a list of query objects")
    return rows


def _record_id(record: dict[str, Any]) -> str | None:
    value = record.get("id") or record.get("record_id") or record.get("pair_id")
    return str(value).strip() if value is not None and str(value).strip() else None


def _match_text_key(record: dict[str, Any]) -> str:
    """Return a stable key for the exact text selected by ``pair_embeddings``."""
    digest = str(record.get("embedding_text_sha256") or "").strip().casefold()
    if digest:
        return f"sha256:{digest}"
    # Backward-compatible fallback for ranking artifacts created before the
    # retriever emitted its exact (possibly title-augmented) text hash.
    text = str(record.get("match_summary") or record.get("identity_text") or "").strip()
    return f"text:{text}" if text else ""


def _multiplicity_bucket(count: int) -> str:
    if count <= 1:
        return "1"
    if count <= 5:
        return "2-5"
    if count <= 20:
        return "6-20"
    return "over-20"


def _corpus_indexes(payload: Any) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not isinstance(payload, dict) or payload.get("corpus_records") is None:
        return [], {}
    records = payload["corpus_records"]
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise ValueError("corpus_records must be a list of objects")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = _record_id(record)
        if not record_id:
            continue
        if record_id in by_id:
            raise ValueError(f"Duplicate corpus record id: {record_id}")
        by_id[record_id] = record
    return records, by_id


def _resolve_candidate_record(
    candidate: dict[str, Any],
    corpus: list[dict[str, Any]],
    corpus_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if isinstance(candidate.get("record"), dict):
        return candidate
    record = None
    if candidate.get("corpus_index") is not None:
        index = candidate["corpus_index"]
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(corpus):
            raise ValueError(f"Invalid corpus_index: {index!r}")
        record = corpus[index]
    declared_id = candidate.get("record_id")
    if declared_id is not None:
        declared_id = str(declared_id).strip()
        by_id = corpus_by_id.get(declared_id)
        if by_id is None:
            raise ValueError(f"Unknown candidate record_id: {declared_id}")
        if record is not None and by_id is not record:
            raise ValueError(f"corpus_index and record_id refer to different records: {declared_id}")
        record = by_id
    if record is None:
        return candidate
    return {**candidate, "record": record}


def load_rankings(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load ranking JSON keyed by query id."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = _unwrap_rows(payload, ("queries", "rankings"))
    corpus, corpus_by_id = _corpus_indexes(payload)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        query = row.get("query") if isinstance(row.get("query"), dict) else {}
        identity = {**query, **{key: value for key, value in row.items() if key != "query"}}
        query_id = _query_id(identity)
        if query_id in out:
            raise ValueError(f"Duplicate ranking query_id: {query_id}")
        candidates = row.get("candidates", row.get("ranking"))
        if not isinstance(candidates, list) or not all(isinstance(candidate, dict) for candidate in candidates):
            raise ValueError(f"{query_id}: candidates must be a list of objects")
        candidates = [_resolve_candidate_record(candidate, corpus, corpus_by_id) for candidate in candidates]
        strata = _strata(query.get("strata")) | _strata(row.get("strata"))
        out[query_id] = {"candidates": candidates, "strata": sorted(strata)}
    return out


def _normalize_pair(row: dict[str, Any], fallback_papers: set[str]) -> tuple[str, frozenset[str]]:
    original = next(iter(_values(row, "doi_o", "original_id", "original_ids")), None)
    papers = _values(row, "doi_r", "paper_id", "paper_ids", "later_id", "later_ids", "aliases")
    # Query-level ids are aliases for this same later-paper entity.  A gold
    # pair written with the journal DOI must therefore also match a retrieved
    # preprint DOI (and vice versa).
    papers.update(fallback_papers)
    if not original or not papers:
        raise ValueError("Each gold pair needs an original id and a later-paper id or alias")
    return original, frozenset(papers)


def normalize_truth_rows(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Normalize custom or repository-derived truth rows."""
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        query_id = _query_id(row)
        if query_id in out:
            raise ValueError(f"Duplicate truth query_id: {query_id}")
        papers = _values(row, "gold_paper_ids", "paper_ids", "aliases")
        papers.update(_values(row, "doi_r"))
        explicit_pairs = row.get("gold_pairs")
        if explicit_pairs is None:
            pair_rows = [row] if row.get("doi_o") and row.get("doi_r") and row.get("pair_positive", True) else []
        else:
            if not isinstance(explicit_pairs, list) or not all(isinstance(pair, dict) for pair in explicit_pairs):
                raise ValueError(f"{query_id}: gold_pairs must be a list of objects")
            pair_rows = explicit_pairs
        pairs = [_normalize_pair(pair, papers) for pair in pair_rows]
        for _, aliases in pairs:
            papers.update(aliases)
        if not papers:
            raise ValueError(f"{query_id}: truth row has no later-paper identifier")
        out[query_id] = {
            "paper_ids": frozenset(papers),
            "pairs": pairs,
            "strata": sorted(_strata(row.get("strata")) or {"unstratified"}),
        }
    return out


def load_truth(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return normalize_truth_rows(_unwrap_rows(payload, ("queries", "truth", "positives")))


def load_embedded_truth(path: str | Path) -> dict[str, dict[str, Any]]:
    """Read exact positives referenced by ``exact_corpus_record_id``.

    This adapter is useful for a frozen summary/ranking artifact whose query
    records already identify their known exact FORRT corpus row.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = _unwrap_rows(payload, ("queries", "rankings"))
    corpus, corpus_by_id = _corpus_indexes(payload)
    match_text_counts: dict[str, int] = defaultdict(int)
    for corpus_record in corpus:
        if text := _match_text_key(corpus_record):
            match_text_counts[text] += 1
    truth_rows = []
    for row in rows:
        query = row.get("query") if isinstance(row.get("query"), dict) else row
        exact_id = query.get("exact_corpus_record_id") or row.get("exact_corpus_record_id")
        if not exact_id:
            continue
        exact_id = str(exact_id).strip()
        record = corpus_by_id.get(exact_id)
        if record is None:
            raise ValueError(f"Unknown exact_corpus_record_id: {exact_id}")
        doi_o = record.get("doi_o")
        doi_r = record.get("doi_r")
        if not doi_o or not doi_r:
            raise ValueError(f"Exact corpus record {exact_id} needs doi_o and doi_r")
        aliases = _values(record, "doi_r", "paper_id", "paper_ids", "later_id", "later_ids", "aliases")
        aliases.update(_side_identifiers(record, "replication"))
        aliases.update(_values(query, "doi_r", "paper_id", "paper_ids", "later_id", "later_ids", "aliases"))
        aliases.update(_side_identifiers(query, "replication"))
        strata = _strata(query.get("strata")) | _strata(row.get("strata")) | {"source=embedded_exact"}
        if record.get("status"):
            strata.add(f"status={record['status']}")
        match_text = _match_text_key(record)
        if not match_text:
            strata.update({
                "semantic_retrieval_coverage=textless_gold",
                "gold_match_text=missing",
                "gold_match_text_multiplicity=missing",
            })
        else:
            multiplicity = match_text_counts[match_text]
            strata.update({
                "semantic_retrieval_coverage=eligible",
                f"gold_match_text={'unique' if multiplicity == 1 else 'duplicate'}",
                f"gold_match_text_multiplicity={_multiplicity_bucket(multiplicity)}",
            })
        truth_rows.append({
            "query_id": _query_id({**query, **{key: value for key, value in row.items() if key != "query"}}),
            "doi_o": doi_o,
            "doi_r": doi_r,
            "gold_paper_ids": sorted(aliases),
            "gold_pairs": [{"doi_o": doi_o, "doi_r": doi_r}],
            "strata": sorted(strata),
        })
    if not truth_rows:
        raise ValueError("Ranking JSON contains no exact_corpus_record_id positives")
    return normalize_truth_rows(truth_rows)


def repository_truth_rows(
    attempts_path: str | Path = ATTEMPTS,
    overlap_audit_path: str | Path = OVERLAP_AUDIT,
) -> list[dict[str, Any]]:
    """Build known paper/pair positives from the current built and audited layers."""
    attempts = json.loads(Path(attempts_path).read_text(encoding="utf-8"))
    overlap = json.loads(Path(overlap_audit_path).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for attempt in attempts.values():
        sources = attempt.get("sources") or []
        if attempt.get("retested_review") is None or not any(source != "retested" for source in sources):
            continue
        rows.append({
            "query_id": query_id_for_pair(attempt.get("doi_o"), attempt.get("doi_r")),
            "doi_o": attempt.get("doi_o"),
            "doi_r": attempt.get("doi_r"),
            "gold_paper_ids": [attempt.get("doi_r")],
            "strata": ["source=built_overlay", "relation=same_pair"],
        })
    for record in overlap.get("records", []):
        relation = record.get("combined_classification")
        if relation not in {"same_pair_recorded", "later_paper_recorded_pair_unconfirmed"}:
            continue
        aliases = {record.get("doi_r")}
        evidence = record.get("evidence") or {}
        aliases.update(evidence.get("source_replication_dois") or [])
        live_match = record.get("live_match") or {}
        aliases.update(live_match.get("source_later_dois") or [])
        aliases.discard(None)
        strata = [
            "source=overlap_audit",
            f"relation={'same_pair' if relation == 'same_pair_recorded' else 'later_paper_only'}",
            f"local_classification={record.get('classification') or 'unknown'}",
        ]
        if live_match.get("match_basis"):
            strata.append(f"live_match_basis={live_match['match_basis']}")
        row = {
            "query_id": query_id_for_pair(record.get("doi_o"), record.get("doi_r")),
            "doi_o": record.get("doi_o"),
            "doi_r": record.get("doi_r"),
            "gold_paper_ids": sorted(aliases),
            "gold_pairs": (
                [{"doi_o": record.get("doi_o"), "doi_r": record.get("doi_r")}]
                if relation == "same_pair_recorded" else []
            ),
            "strata": strata,
        }
        rows.append(row)
    return rows


def load_repository_truth(
    attempts_path: str | Path = ATTEMPTS,
    overlap_audit_path: str | Path = OVERLAP_AUDIT,
) -> dict[str, dict[str, Any]]:
    return normalize_truth_rows(repository_truth_rows(attempts_path, overlap_audit_path))


def _candidate_papers(candidate: dict[str, Any]) -> set[str]:
    papers = _values(candidate, "doi_r", "paper_id", "paper_ids", "later_id", "later_ids", "aliases")
    papers.update(_side_identifiers(candidate, "replication"))
    for key in ("paper", "record"):
        nested = candidate.get(key)
        if isinstance(nested, dict):
            papers.update(_values(nested, "doi_r", "paper_id", "paper_ids", "id", "aliases"))
            papers.update(_side_identifiers(nested, "replication"))
    return papers


def _candidate_pairs(candidate: dict[str, Any], papers: set[str]) -> list[tuple[str, frozenset[str]]]:
    rows: list[dict[str, Any]] = []
    if candidate.get("doi_o") or candidate.get("original_id") or candidate.get("original_ids"):
        rows.append(candidate)
    nested = candidate.get("pair")
    if isinstance(nested, dict):
        rows.append(nested)
    nested_many = candidate.get("pairs")
    if isinstance(nested_many, list):
        rows.extend(pair for pair in nested_many if isinstance(pair, dict))
    record = candidate.get("record")
    if isinstance(record, dict):
        rows.append(record)
        record_pairs = record.get("pairs")
        if isinstance(record_pairs, list):
            rows.extend(pair for pair in record_pairs if isinstance(pair, dict))
    out = []
    for row in rows:
        original_ids = _values(row, "doi_o", "original_id", "original_ids")
        original_ids.update(_side_identifiers(row, "original"))
        later_ids = _values(row, "doi_r", "paper_id", "paper_ids", "later_id", "later_ids", "aliases") or papers
        later_ids.update(_side_identifiers(row, "replication"))
        out.extend((original, frozenset(later_ids)) for original in original_ids if later_ids)
    return out


def _first_ranks(candidates: list[dict[str, Any]], truth: dict[str, Any]) -> tuple[int | None, int | None]:
    paper_rank = None
    pair_rank = None
    for rank, candidate in enumerate(candidates, 1):
        papers = _candidate_papers(candidate)
        if paper_rank is None and papers & truth["paper_ids"]:
            paper_rank = rank
        if pair_rank is None and truth["pairs"]:
            for candidate_original, candidate_papers in _candidate_pairs(candidate, papers):
                if any(
                    candidate_original == gold_original and candidate_papers & gold_papers
                    for gold_original, gold_papers in truth["pairs"]
                ):
                    pair_rank = rank
                    break
        if paper_rank is not None and (pair_rank is not None or not truth["pairs"]):
            break
    return paper_rank, pair_rank


def _metric(ranks: list[int | None], ks: tuple[int, ...]) -> dict[str, Any]:
    total = len(ranks)
    hits = {
        str(k): {
            "hits": sum(rank is not None and rank <= k for rank in ranks),
            "total": total,
            "rate": round(sum(rank is not None and rank <= k for rank in ranks) / total, 6) if total else None,
        }
        for k in ks
    }
    reciprocal = sum(1 / rank for rank in ranks if rank is not None)
    return {
        "queries": total,
        "retrieved": sum(rank is not None for rank in ranks),
        "unretrieved": sum(rank is None for rank in ranks),
        "mrr": round(reciprocal / total, 6) if total else None,
        "hit_at": hits,
    }


def _summarize(query_ids: Iterable[str], evaluated: dict[str, dict[str, Any]], ks: tuple[int, ...]) -> dict[str, Any]:
    ids = list(query_ids)
    records = [evaluated[query_id] for query_id in ids]
    max_k = ks[-1]
    return {
        "truth_queries": len(records),
        "queries_with_rankings": sum(record["has_ranking"] for record in records),
        "paper": _metric([record["paper_rank"] for record in records], ks),
        "pair": _metric([record["pair_rank"] for record in records if record["has_pair_truth"]], ks),
        "paper_miss_query_ids_at_max_k": [
            query_id for query_id in ids
            if evaluated[query_id]["paper_rank"] is None or evaluated[query_id]["paper_rank"] > max_k
        ],
        "pair_miss_query_ids_at_max_k": [
            query_id for query_id in ids
            if evaluated[query_id]["has_pair_truth"]
            and (evaluated[query_id]["pair_rank"] is None or evaluated[query_id]["pair_rank"] > max_k)
        ],
    }


def evaluate(
    rankings: dict[str, dict[str, Any]],
    truth: dict[str, dict[str, Any]],
    ks: Iterable[int] = DEFAULT_KS,
) -> dict[str, Any]:
    """Evaluate supplied ranked candidates against paper and pair positives."""
    normalized_ks = tuple(sorted({int(k) for k in ks}))
    if not normalized_ks or normalized_ks[0] <= 0:
        raise ValueError("ks must contain positive integers")
    evaluated: dict[str, dict[str, Any]] = {}
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for query_id, gold in truth.items():
        ranking = rankings.get(query_id)
        candidates = ranking["candidates"] if ranking else []
        paper_rank, pair_rank = _first_ranks(candidates, gold)
        strata = set(gold["strata"])
        if ranking:
            strata.update(ranking.get("strata") or [])
        if not strata:
            strata.add("unstratified")
        evaluated[query_id] = {
            "has_ranking": ranking is not None,
            "has_pair_truth": bool(gold["pairs"]),
            "paper_rank": paper_rank,
            "pair_rank": pair_rank,
        }
        for stratum in sorted(strata):
            by_stratum[stratum].append(query_id)
    overall = _summarize(truth, evaluated, normalized_ks)
    unknown = sorted(set(rankings) - set(truth))
    return {
        "ks": list(normalized_ks),
        "rank_unit": "candidate_rows",
        "truth_queries": len(truth),
        "ranking_queries": len(rankings),
        "unknown_ranking_queries": len(unknown),
        "unknown_ranking_query_ids": unknown,
        "overall": overall,
        "strata_are_nonexclusive": True,
        "by_stratum": {
            stratum: _summarize(query_ids, evaluated, normalized_ks)
            for stratum, query_ids in sorted(by_stratum.items())
        },
    }


def _parse_ks(value: str) -> tuple[int, ...]:
    try:
        ks = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("--ks must be comma-separated integers") from error
    if not ks or any(k <= 0 for k in ks):
        raise argparse.ArgumentTypeError("--ks must contain positive integers")
    return ks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rankings", type=Path, help="Precomputed ranked-candidate JSON")
    truth_group = parser.add_mutually_exclusive_group()
    truth_group.add_argument("--truth", type=Path, help="Optional custom benchmark truth JSON")
    truth_group.add_argument("--embedded-truth", action="store_true", help="Use exact_corpus_record_id positives in the ranking JSON")
    parser.add_argument("--attempts", type=Path, default=ATTEMPTS, help="Built attempts used for repository truth")
    parser.add_argument("--overlap-audit", type=Path, default=OVERLAP_AUDIT, help="FORRT overlap audit used for repository truth")
    parser.add_argument("--ks", type=_parse_ks, default=DEFAULT_KS, help="Hit-rate cutoffs (default: 1,3,5,10,20,50)")
    parser.add_argument("--output", type=Path, help="Write JSON here instead of stdout")
    args = parser.parse_args()
    rankings = load_rankings(args.rankings)
    if args.truth:
        truth = load_truth(args.truth)
    elif args.embedded_truth:
        truth = load_embedded_truth(args.rankings)
    else:
        truth = load_repository_truth(args.attempts, args.overlap_audit)
    rendered = json.dumps(evaluate(rankings, truth, args.ks), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
