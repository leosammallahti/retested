"""Build a reproducible source-review queue from pair-match rankings.

The existing FORRT overlap audit decides exact DOI/title cases.  This module
joins every still-unconfirmed audit row to its semantic ranking, expands the
top candidate references, and sorts likely hidden overlaps first.  It does not
make an overlap decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .load import ROOT
from .pair_summaries import canonical_doi

DEFAULT_RANKINGS = ROOT / "data" / "discovery" / "pair_match_candidates.json"
DEFAULT_AUDIT = ROOT / "data" / "curated" / "forrt_overlap_audit_20260926.json"
DEFAULT_OUTPUT = ROOT / "data" / "discovery" / "pair_match_review_queue.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pair(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    return canonical_doi(row.get("doi_o")), canonical_doi(row.get("doi_r"))


def _query(row: Mapping[str, Any]) -> Mapping[str, Any]:
    query = row.get("query")
    if not isinstance(query, Mapping):
        raise ValueError("Each ranking row needs a query object")
    return query


def build_queue(rankings_path: Path, audit_path: Path, *, top_k: int = 10) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    rankings = json.loads(rankings_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    ranking_rows = rankings.get("queries") if isinstance(rankings, dict) else None
    corpus = rankings.get("corpus_records") if isinstance(rankings, dict) else None
    audit_rows = audit.get("records") if isinstance(audit, dict) else None
    if not isinstance(ranking_rows, list) or not all(isinstance(row, dict) for row in ranking_rows):
        raise ValueError("Rankings JSON needs a queries list")
    if not isinstance(corpus, list) or not all(isinstance(row, dict) for row in corpus):
        raise ValueError("Rankings JSON needs a corpus_records list")
    if not isinstance(audit_rows, list) or not all(isinstance(row, dict) for row in audit_rows):
        raise ValueError("Audit JSON needs a records list")

    rankings_by_pair: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for row in ranking_rows:
        key = _pair(_query(row))
        if not all(key):
            raise ValueError(f"Ranking query lacks a canonical pair: {key}")
        if key in rankings_by_pair:
            raise ValueError(f"Duplicate ranking pair: {key}")
        rankings_by_pair[key] = row

    records: list[dict[str, Any]] = []
    unmapped: list[dict[str, Any]] = []
    selected_audit_rows = 0
    for audit_index, audit_row in enumerate(audit_rows):
        prior = audit_row.get("combined_classification")
        if prior == "same_pair_recorded":
            continue
        selected_audit_rows += 1
        key = _pair(audit_row)
        ranking = rankings_by_pair.get(key)
        if ranking is None:
            unmapped.append({
                "audit_record_index": audit_index,
                "doi_o": audit_row.get("doi_o"),
                "doi_r": audit_row.get("doi_r"),
                "canonical_pair": list(key),
                "prior_classification": prior,
            })
            continue
        expanded = []
        candidates = ranking.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"Ranking for {key} lacks candidates")
        for candidate in candidates[:top_k]:
            if not isinstance(candidate, dict):
                raise ValueError(f"Ranking for {key} contains a non-object candidate")
            corpus_index = candidate.get("corpus_index")
            if not isinstance(corpus_index, int) or isinstance(corpus_index, bool) or not 0 <= corpus_index < len(corpus):
                raise ValueError(f"Ranking for {key} has invalid corpus index {corpus_index!r}")
            record = corpus[corpus_index]
            if candidate.get("record_id") != record.get("id"):
                raise ValueError(f"Ranking for {key} has inconsistent candidate id/index")
            expanded.append({**candidate, "record": record})
        top_score = expanded[0].get("cosine_similarity") if expanded else None
        records.append({
            "audit_record_index": audit_index,
            "query": dict(_query(ranking)),
            "prior_classification": prior,
            "candidates": expanded,
            "top_score": top_score,
            **({"boundary_tie": ranking["boundary_tie"]} if "boundary_tie" in ranking else {}),
        })

    records.sort(key=lambda row: (
        -(row["top_score"] if isinstance(row["top_score"], (int, float)) else float("-inf")),
        str(row["query"].get("id") or ""),
    ))
    return {
        "schema_version": 1,
        "purpose": "human source-review queue; ranking score is candidate retrieval, not an overlap decision",
        "inputs": {
            "rankings": {"path": str(rankings_path), "sha256": _sha256(rankings_path)},
            "overlap_audit": {"path": str(audit_path), "sha256": _sha256(audit_path)},
        },
        "counts": {
            "audit_records": len(audit_rows),
            "audit_rows_not_already_same_pair": selected_audit_rows,
            "mapped_queue_records": len(records),
            "unmapped_audit_records": len(unmapped),
            "candidates_per_query": top_k,
        },
        "unmapped_audit_records": unmapped,
        "records": records,
    }


def write_queue(payload: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=output.name + ".", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        os.chmod(temporary, 0o644)
        Path(temporary).replace(output)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rankings", type=Path, default=DEFAULT_RANKINGS)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args(argv)
    payload = build_queue(args.rankings, args.audit, top_k=args.top_k)
    write_queue(payload, args.output)
    counts = payload["counts"]
    print(
        f"WROTE {args.output} mapped={counts['mapped_queue_records']} "
        f"unmapped={counts['unmapped_audit_records']} top_k={counts['candidates_per_query']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
