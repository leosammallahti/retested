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


def append_source_identity_review(
    ledger: Mapping[str, Any],
    review_path: Path,
    summaries_path: Path,
    audit_path: Path,
) -> dict[str, Any]:
    """Append a bounded non-embedding Work-identity review to a semantic ledger.

    Some bibliographic candidates are found by title/alternate-identifier
    reconciliation rather than the frozen embedding queue.  Their decisions
    still need the same durable query/candidate snapshots and evidence fields,
    but must not be assigned a fictional embedding rank.  This helper retains
    the original ledger intact, appends those source reviews with a null queue
    index, and records the distinct review artifact and its digest.
    """

    merged = json.loads(json.dumps(ledger))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    decisions = review.get("decisions") if isinstance(review, Mapping) else None
    if not isinstance(decisions, list) or not all(isinstance(row, Mapping) for row in decisions):
        raise ValueError("source identity review needs a decisions list")
    summaries = json.loads(summaries_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    queries = {str(row["record_id"]): row for row in summaries.get("query_records") or []}
    candidates = {str(row["record_id"]): row for row in summaries.get("corpus_records") or []}
    audit_by_pair = {
        (str(row.get("doi_o")), str(row.get("doi_r"))): row
        for row in audit.get("records") or []
    }
    existing = {str(row.get("query_record_id")) for row in merged.get("decisions") or []}
    added: list[dict[str, Any]] = []
    for raw in decisions:
        query_id = str(raw.get("query_record_id") or "")
        if not query_id or query_id not in queries:
            raise ValueError(f"source identity review query absent from pair summaries: {query_id!r}")
        if query_id in existing:
            raise ValueError(f"source identity review duplicates an existing query: {query_id}")
        decision = str(raw.get("decision") or "")
        if decision not in DECISIONS - {"related_but_distinct", "unresolved"}:
            raise ValueError(f"{query_id}: source identity review has unsupported decision {decision!r}")
        selected = [str(value) for value in raw.get("candidate_record_ids") or []]
        if not selected or any(value not in candidates for value in selected):
            raise ValueError(f"{query_id}: source identity review has no valid frozen candidate linkage")
        query = queries[query_id]
        doi_o, doi_r = str(raw.get("doi_o")), str(raw.get("doi_r"))
        if (query.get("doi_o"), query.get("doi_r")) != (doi_o, doi_r):
            raise ValueError(f"{query_id}: source identity review DOI pair disagrees with query")
        prior = audit_by_pair.get((doi_o, doi_r))
        if prior is None:
            raise ValueError(f"{query_id}: source identity review pair absent from overlap audit")
        original_matches, later_matches = _matches(raw, decision)
        if (original_matches, later_matches) not in {(True, True), (False, True)}:
            raise ValueError(f"{query_id}: source identity review must state ordered Work matches")
        locations = _evidence_locations(raw)
        if not raw.get("evidence") or not locations:
            raise ValueError(f"{query_id}: source identity review lacks evidence or stable locations")
        reviewer_record = dict(raw)
        reviewer_record["review_method"] = "bounded_source_identity_review_outside_embedding_queue"
        reviewer_record["scientific_equivalence_axes"] = "not_compared"
        added.append({
            "queue_index": None,
            "query_record_id": query_id,
            "doi_o": doi_o,
            "doi_r": doi_r,
            "prior_classification": prior.get("combined_classification"),
            "top_cosine_similarity": None,
            "decision": decision,
            "original_work_matches": original_matches,
            "later_work_matches": later_matches,
            "candidate_record_ids": selected,
            "evidence": raw.get("evidence"),
            "evidence_locations": locations,
            "query_snapshot": query,
            "candidate_snapshots": [candidates[value] for value in selected],
            "reviewer_record": reviewer_record,
        })
        existing.add(query_id)

    merged["decisions"] = list(merged.get("decisions") or []) + added
    merged["decisions"].sort(key=lambda row: (
        row.get("queue_index") is None,
        row.get("queue_index") if row.get("queue_index") is not None else float("inf"),
        str(row.get("query_record_id")),
    ))
    descriptor = {
        "path": str(review_path.relative_to(ROOT)),
        "sha256": _sha256(review_path),
        "reviewed_at_utc": review.get("reviewed_at_utc"),
        "decisions": len(added),
        "packet_metadata": {key: value for key, value in review.items() if key != "decisions"},
    }
    merged["decision_sources"] = list(merged.get("decision_sources") or []) + [descriptor]
    merged["direct_source_identity_review"] = {
        "path": descriptor["path"],
        "sha256": descriptor["sha256"],
        "decisions": len(added),
        "scientific_equivalence_axes": "not_compared",
    }
    counts = Counter(str(row.get("decision")) for row in merged["decisions"])
    summary = dict(merged.get("summary") or {})
    summary["reviewed_queries"] = len(merged["decisions"])
    summary["embedding_queue_queries_reviewed"] = sum(
        row.get("queue_index") is not None for row in merged["decisions"]
    )
    summary["direct_source_identity_queries_reviewed"] = len(added)
    summary["queue_indexes_reviewed"] = [
        row["queue_index"] for row in merged["decisions"] if row.get("queue_index") is not None
    ]
    summary["counts"] = {decision: counts.get(decision, 0) for decision in sorted(DECISIONS)}
    merged["summary"] = summary
    return merged


def repair_existing_evidence(ledger: Mapping[str, Any], repair_path: Path) -> dict[str, Any]:
    """Apply a source-reviewed rationale/location repair without changing a decision.

    Negative retrieval decisions are not evidence of absence, but each still
    needs a durable explanation of why its reviewed candidate is distinct.
    A repair packet may fill only a missing rationale or missing locator on an
    existing ``related_but_distinct`` decision; it cannot alter its label,
    selected candidates, or any scientific-equivalence field.
    """

    merged = json.loads(json.dumps(ledger))
    repair = json.loads(repair_path.read_text(encoding="utf-8"))
    rows = repair.get("repairs") if isinstance(repair, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("negative-evidence repair needs a repairs list")
    by_query = {str(row.get("query_record_id")): row for row in merged.get("decisions") or []}
    seen: set[str] = set()
    for source in rows:
        query_id = str(source.get("query_record_id") or "")
        if not query_id or query_id in seen or query_id not in by_query:
            raise ValueError(f"invalid or duplicate negative-evidence repair query: {query_id!r}")
        seen.add(query_id)
        target = by_query[query_id]
        if target.get("decision") != "related_but_distinct":
            raise ValueError(f"{query_id}: evidence repair may only amend related_but_distinct")
        # A location-only repair preserves an already reviewed rationale.
        evidence = source.get("evidence") or target.get("evidence")
        locations = _evidence_locations(source)
        if not str(evidence or "").strip() or not locations:
            raise ValueError(f"{query_id}: evidence repair lacks rationale or locations")
        if any(str(location.get("path") or "").startswith("/tmp/") for location in locations):
            raise ValueError(f"{query_id}: evidence repair contains an ephemeral locator")
        if target.get("evidence") and target.get("evidence_locations"):
            raise ValueError(f"{query_id}: evidence repair would overwrite a complete decision")
        target["evidence"] = evidence
        target["evidence_locations"] = locations
        reviewer = dict(target.get("reviewer_record") or {})
        reviewer["evidence_repair"] = {
            "artifact": str(repair_path.relative_to(ROOT)),
            "evidence": evidence,
            "evidence_locations": locations,
            "scientific_equivalence_axes": "not_compared",
        }
        target["reviewer_record"] = reviewer

    descriptor = {
        "path": str(repair_path.relative_to(ROOT)),
        "sha256": _sha256(repair_path),
        "reviewed_at_utc": repair.get("reviewed_at_utc"),
        "repairs": len(rows),
        "packet_metadata": {key: value for key, value in repair.items() if key != "repairs"},
    }
    merged["evidence_repair_sources"] = list(merged.get("evidence_repair_sources") or []) + [descriptor]
    return merged


def retract_unsupported_evidence_repairs(ledger: Mapping[str, Any], correction_path: Path) -> dict[str, Any]:
    """Re-open a negative decision when a prior repair lacked Work evidence.

    An unmatched DOI is not enough to establish distinct Works.  This records
    the correction durably, retains any valid source locations, and restores
    the missing-rationale state rather than silently preserving an overclaim.
    """

    merged = json.loads(json.dumps(ledger))
    correction = json.loads(correction_path.read_text(encoding="utf-8"))
    rows = correction.get("retractions") if isinstance(correction, Mapping) else None
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("negative-evidence correction needs a retractions list")
    by_query = {str(row.get("query_record_id")): row for row in merged.get("decisions") or []}
    for source in rows:
        query_id = str(source.get("query_record_id") or "")
        target = by_query.get(query_id)
        if target is None or target.get("decision") != "related_but_distinct":
            raise ValueError(f"invalid negative-evidence correction query: {query_id!r}")
        if not str(source.get("reason") or "").strip():
            raise ValueError(f"{query_id}: correction lacks a reason")
        target["evidence"] = None
        reviewer = dict(target.get("reviewer_record") or {})
        reviewer["evidence_repair_retraction"] = {
            "artifact": str(correction_path.relative_to(ROOT)),
            "reason": source["reason"],
            "scientific_equivalence_axes": "not_compared",
        }
        target["reviewer_record"] = reviewer
    merged["evidence_repair_corrections"] = list(merged.get("evidence_repair_corrections") or []) + [{
        "path": str(correction_path.relative_to(ROOT)),
        "sha256": _sha256(correction_path),
        "reviewed_at_utc": correction.get("reviewed_at_utc"),
        "retractions": len(rows),
    }]
    return merged


def attach_independent_work_identity_review(
    ledger: Mapping[str, Any], review_path: Path,
) -> dict[str, Any]:
    """Record a bounded, independent bibliographic identity re-review.

    This is deliberately provenance rather than a new semantic adjudication:
    it cannot change the original decision or upgrade any scientific axis.  A
    second reviewer may agree while documenting an evidence gap, so coverage
    remains partial even when every record in the small reviewed subset agrees.
    """

    merged = json.loads(json.dumps(ledger))
    packet = json.loads(review_path.read_text(encoding="utf-8"))
    reviews = packet.get("reviews") if isinstance(packet, Mapping) else None
    summary = packet.get("summary") if isinstance(packet, Mapping) else None
    if not isinstance(reviews, list) or not all(isinstance(row, Mapping) for row in reviews):
        raise ValueError("independent identity review needs a reviews list")
    if not isinstance(summary, Mapping):
        raise ValueError("independent identity review needs a summary")
    required_statuses = {"agree", "agree_with_evidence_gap"}
    if any(str(row.get("second_review_status")) not in required_statuses for row in reviews):
        raise ValueError("independent identity review has an unsupported review status")
    if int(summary.get("disagreements", -1)) != 0:
        raise ValueError("an independent disagreement requires a separate adjudication")

    by_query = {str(row.get("query_record_id")): row for row in merged.get("decisions") or []}
    seen: set[str] = set()
    attached = 0
    packet_reference = {
        "path": str(review_path.relative_to(ROOT)),
        "sha256": _sha256(review_path),
        "reviewed_at_utc": packet.get("reviewed_at_utc"),
        "scope": packet.get("scope"),
    }
    for review in reviews:
        query_id = str(review.get("query_record_id") or "")
        candidate_id = str(review.get("candidate_record_id") or "")
        if not query_id or not candidate_id or query_id in seen:
            raise ValueError(f"invalid or duplicate independent review query: {query_id!r}")
        seen.add(query_id)
        target = by_query.get(query_id)
        if target is None or candidate_id not in set(target.get("candidate_record_ids") or []):
            raise ValueError(f"{query_id}: independent review does not match a source-adjudicated pair")
        if target.get("decision") not in {
            "confirmed_same_pair", "confirmed_same_later_version_same_pair",
        }:
            raise ValueError(f"{query_id}: independent review cannot alter a non-positive identity decision")
        target["independent_work_identity_review"] = {
            **packet_reference,
            "candidate_record_id": candidate_id,
            "second_review_status": review["second_review_status"],
            "ordered_work_identity": review.get("ordered_work_identity"),
            "basis": review.get("basis"),
            "evidence_gaps": review.get("evidence_gaps") or [],
            "coverage": "partial_independent_bibliographic_work_identity_only",
            "scientific_equivalence_axes": "not_compared",
        }
        attached += 1

    if attached != int(summary.get("positive_first_review_decisions_reviewed", -1)):
        raise ValueError("independent review count disagrees with its summary")
    merged["independent_work_identity_review"] = {
        **packet_reference,
        "reviewed_positive_direct_source_identity_decisions": attached,
        "full_agreements": int(summary.get("full_agreements", 0)),
        "agreements_with_material_evidence_gap": int(summary.get("agreements_with_material_evidence_gap", 0)),
        "disagreements": int(summary.get("disagreements", 0)),
        "coverage": "partial: this is an independent bibliographic Work-identity review of the eight directly source-adjudicated positive candidates only; it is not full-registry assurance",
        "scientific_equivalence_axes": "not_compared",
        "required_follow_up": summary.get("required_follow_up"),
    }
    return merged


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
