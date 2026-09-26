"""Validate and preserve human decisions from a semantic pair-match queue.

Embeddings only retrieve candidates.  This module turns source-review packets
into a durable, lossless ledger after checking that every reviewed query and
candidate really occurred in the frozen queue supplied to the reviewers.

The reviewer packets used during the first audit were produced by several
parallel sessions and intentionally have slightly different surface schemas.
The normalizer keeps each original record under ``reviewer_record`` while also
emitting common fields for counting and downstream audit updates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .load import ROOT

DEFAULT_OUTPUT = ROOT / "data" / "curated" / "forrt_semantic_match_review_20260926.json"

DECISIONS = {
    "confirmed_same_pair",
    "confirmed_same_later_version_same_pair",
    "same_later_work_different_original",
    "related_but_distinct",
    "unresolved",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(payload: object, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get(key)
    else:
        rows = None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"JSON must contain a {key!r} list of objects")
    return rows


def _queue_query_id(row: Mapping[str, Any]) -> str:
    query = row.get("query")
    if not isinstance(query, Mapping):
        raise ValueError("Each queue row needs a query object")
    value = query.get("id") or query.get("record_id") or query.get("pair_id")
    if value is None or not str(value).strip():
        raise ValueError("Each queue query needs an id")
    return str(value).strip()


def _decision_query_id(row: Mapping[str, Any]) -> str:
    value = row.get("query_record_id") or row.get("query_id")
    query = row.get("query")
    if not value and isinstance(query, Mapping):
        value = query.get("record_id") or query.get("id") or query.get("pair_id")
    if value is None or not str(value).strip():
        raise ValueError("Each decision needs a query record id")
    return str(value).strip()


def _candidate_ids(row: Mapping[str, Any]) -> list[str]:
    found: list[str] = []
    values = row.get("candidate_record_ids")
    if isinstance(values, list):
        found.extend(str(value).strip() for value in values if str(value).strip())
    assessments = row.get("candidate_assessments")
    if isinstance(assessments, list):
        for item in assessments:
            if isinstance(item, Mapping):
                value = item.get("record_id") or item.get("candidate_record_id")
                if value is not None and str(value).strip():
                    found.append(str(value).strip())
    value = row.get("candidate_record_id")
    if value is not None and str(value).strip():
        found.append(str(value).strip())
    return list(dict.fromkeys(found))


def _location(value: object, kind: str | None = None) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        item = {str(key): content for key, content in value.items() if content is not None}
        return item or None
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    if kind:
        return {kind: text}
    return {"url" if text.startswith(("http://", "https://")) else "path": text}


def _evidence_locations(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for key in ("sources", "evidence_locations", "evidence_paths"):
        items = row.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if normalized := _location(item):
                values.append(normalized)
    urls = row.get("evidence_urls")
    if isinstance(urls, list):
        for item in urls:
            if normalized := _location(item, "url"):
                values.append(normalized)
    unique: dict[str, dict[str, Any]] = {}
    for item in values:
        unique.setdefault(json.dumps(item, ensure_ascii=False, sort_keys=True), item)
    return list(unique.values())


def _matches(row: Mapping[str, Any], decision: str) -> tuple[bool | None, bool | None]:
    original = row.get("original_work_matches", row.get("original_match"))
    later = row.get("later_work_matches", row.get("later_match"))
    if decision in {"confirmed_same_pair", "confirmed_same_later_version_same_pair"}:
        return True, True
    if decision == "same_later_work_different_original":
        return False, True
    return (
        original if isinstance(original, bool) else None,
        later if isinstance(later, bool) else None,
    )


def _source_time(payload: Mapping[str, Any], path: Path) -> str:
    value = payload.get("reviewed_at_utc")
    if value is not None and str(value).strip():
        return str(value).strip()
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def build_ledger(queue_path: Path, decision_paths: Iterable[Path]) -> dict[str, Any]:
    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    queue_rows = _records(queue_payload, "records")
    queue_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, row in enumerate(queue_rows):
        query_id = _queue_query_id(row)
        if query_id in queue_by_id:
            raise ValueError(f"Duplicate query id in queue: {query_id}")
        queue_by_id[query_id] = (index, row)

    normalized: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen_queries: set[str] = set()
    for path in decision_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _records(payload, "decisions")
        sources.append({
            "path": str(path),
            "sha256": _sha256(path),
            "reviewed_at_utc": _source_time(payload if isinstance(payload, Mapping) else {}, path),
            "decisions": len(rows),
            "packet_metadata": (
                {key: value for key, value in payload.items() if key != "decisions"}
                if isinstance(payload, Mapping) else {}
            ),
        })
        for reviewer_row in rows:
            query_id = _decision_query_id(reviewer_row)
            if query_id in seen_queries:
                raise ValueError(f"Query reviewed more than once: {query_id}")
            seen_queries.add(query_id)
            if query_id not in queue_by_id:
                raise ValueError(f"Decision query is absent from frozen queue: {query_id}")
            queue_index, queue_row = queue_by_id[query_id]
            decision = str(reviewer_row.get("decision") or "").strip()
            if decision not in DECISIONS:
                raise ValueError(f"{query_id}: invalid decision {decision!r}")
            selected = _candidate_ids(reviewer_row)
            available = {
                str(item.get("record_id")).strip()
                for item in queue_row.get("candidates", [])
                if isinstance(item, Mapping) and item.get("record_id") is not None
            }
            unknown = sorted(set(selected) - available)
            if unknown:
                raise ValueError(f"{query_id}: candidate ids absent from frozen queue: {', '.join(unknown)}")
            if decision != "unresolved" and not selected:
                raise ValueError(f"{query_id}: a resolved decision must identify at least one reviewed candidate")

            query = queue_row["query"]
            candidates_by_id = {
                str(item["record_id"]): item
                for item in queue_row.get("candidates", [])
                if isinstance(item, Mapping) and item.get("record_id") is not None
            }
            original_match, later_match = _matches(reviewer_row, decision)
            normalized.append({
                "queue_index": queue_index,
                "query_record_id": query_id,
                "doi_o": query.get("doi_o"),
                "doi_r": query.get("doi_r"),
                "prior_classification": queue_row.get("prior_classification"),
                "top_cosine_similarity": queue_row.get("top_score"),
                "decision": decision,
                "original_work_matches": original_match,
                "later_work_matches": later_match,
                "candidate_record_ids": selected,
                "evidence": reviewer_row.get("evidence"),
                "evidence_locations": _evidence_locations(reviewer_row),
                # Keep the scientific input, not only a temporary record id.
                # This makes the curated ledger independently inspectable when
                # /tmp is cleared or a later normalization changes record ids.
                "query_snapshot": query,
                "candidate_snapshots": [candidates_by_id[value] for value in selected],
                # Preserve every reviewer nuance and candidate-level assessment.
                "reviewer_record": reviewer_row,
            })

    normalized.sort(key=lambda row: (row["queue_index"], row["query_record_id"]))
    counts = Counter(row["decision"] for row in normalized)
    indexes = [row["queue_index"] for row in normalized]
    return {
        "schema_version": 1,
        "purpose": "source adjudication of embedding-retrieved FORRT overlap candidates; similarity alone is never a decision",
        "frozen_queue": {
            "path": str(queue_path),
            "sha256": _sha256(queue_path),
            "records": len(queue_rows),
        },
        "decision_sources": sources,
        "summary": {
            "reviewed_queries": len(normalized),
            "queue_records": len(queue_rows),
            "queue_indexes_reviewed": indexes,
            "counts": {decision: counts.get(decision, 0) for decision in sorted(DECISIONS)},
        },
        "decisions": normalized,
    }


def write_ledger(payload: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
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
    parser.add_argument("queue", type=Path)
    parser.add_argument("decisions", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    payload = build_ledger(args.queue, args.decisions)
    write_ledger(payload, args.output)
    counts = " ".join(f"{key}={value}" for key, value in payload["summary"]["counts"].items())
    print(f"WROTE {args.output} reviewed={payload['summary']['reviewed_queries']} {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
