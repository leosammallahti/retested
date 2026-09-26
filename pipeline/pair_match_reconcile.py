"""Apply source-adjudicated semantic matches to the exact FORRT audit.

The exact audit remains untouched.  This produces a derived, provenance-rich
view in which only positive human decisions can strengthen a classification.
Rejecting one semantic candidate never proves absence from FORRT, so
``related_but_distinct`` and ``unresolved`` leave the prior class unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .load import ROOT
from .pair_summaries import canonical_doi

DEFAULT_AUDIT = ROOT / "data" / "curated" / "forrt_overlap_audit_20260926.json"
DEFAULT_LEDGER = ROOT / "data" / "curated" / "forrt_semantic_match_review_20260926.json"
DEFAULT_OUTPUT = ROOT / "data" / "curated" / "forrt_overlap_reconciled_20260926.json"

SAME_PAIR_DECISIONS = {"confirmed_same_pair", "confirmed_same_later_version_same_pair"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pair(row: Mapping[str, Any]) -> tuple[str | None, str | None]:
    return canonical_doi(row.get("doi_o")), canonical_doi(row.get("doi_r"))


def reconcile(audit_path: Path, ledger_paths: Path | Sequence[Path]) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit_rows = audit.get("records") if isinstance(audit, dict) else None
    if not isinstance(audit_rows, list) or not all(isinstance(row, dict) for row in audit_rows):
        raise ValueError("Audit JSON needs a records list")
    paths = [ledger_paths] if isinstance(ledger_paths, Path) else list(ledger_paths)
    if not paths:
        raise ValueError("At least one adjudication ledger is required")
    decisions: list[dict[str, Any]] = []
    ledger_inputs = []
    for ledger_path in paths:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        rows = ledger.get("decisions") if isinstance(ledger, dict) else None
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"Adjudication ledger needs a decisions list: {ledger_path}")
        decisions.extend(rows)
        ledger_inputs.append({"path": str(ledger_path), "sha256": _sha256(ledger_path), "decisions": len(rows)})

    audit_by_pair: dict[tuple[str | None, str | None], int] = {}
    for index, row in enumerate(audit_rows):
        key = _pair(row)
        if not all(key):
            raise ValueError(f"Audit row {index} lacks a canonical DOI pair")
        if key in audit_by_pair:
            raise ValueError(f"Duplicate audit pair: {key}")
        audit_by_pair[key] = index

    decision_by_pair: dict[tuple[str | None, str | None], dict[str, Any]] = {}
    for decision in decisions:
        key = _pair(decision)
        if not all(key):
            raise ValueError(f"Adjudication lacks a canonical DOI pair: {decision.get('query_record_id')}")
        if key not in audit_by_pair:
            raise ValueError(f"Adjudicated pair is absent from overlap audit: {key}")
        if key in decision_by_pair:
            raise ValueError(f"Pair adjudicated more than once: {key}")
        decision_by_pair[key] = decision

    records: list[dict[str, Any]] = []
    transitions: Counter[tuple[str, str]] = Counter()
    decision_counts: Counter[str] = Counter()
    for audit_row in audit_rows:
        prior = str(audit_row.get("combined_classification") or "unknown")
        decision = decision_by_pair.get(_pair(audit_row))
        reconciled = prior
        semantic = None
        if decision:
            label = str(decision["decision"])
            decision_counts[label] += 1
            if label in SAME_PAIR_DECISIONS:
                reconciled = "same_pair_recorded"
            elif label == "same_later_work_different_original":
                reconciled = "later_paper_recorded_pair_unconfirmed"
            semantic = {
                "query_record_id": decision.get("query_record_id"),
                "decision": label,
                "candidate_record_ids": decision.get("candidate_record_ids") or [],
                "original_work_matches": decision.get("original_work_matches"),
                "later_work_matches": decision.get("later_work_matches"),
                "top_cosine_similarity": decision.get("top_cosine_similarity"),
                "evidence": decision.get("evidence"),
                "evidence_locations": decision.get("evidence_locations") or [],
                "independent_work_identity_review": decision.get("independent_work_identity_review"),
            }
        transitions[(prior, reconciled)] += 1
        records.append({
            **audit_row,
            "reconciled_classification": reconciled,
            **({"semantic_adjudication": semantic} if semantic else {}),
        })

    classes = Counter(row["reconciled_classification"] for row in records)
    same = classes.get("same_pair_recorded", 0)
    later = classes.get("later_paper_recorded_pair_unconfirmed", 0)
    no_exact = classes.get("no_exact_doi_or_title_match", 0)
    return {
        "schema_version": 1,
        "purpose": "derived overlap audit; positive semantic decisions are source-adjudicated, rejections do not prove absence",
        "inputs": {
            "exact_overlap_audit": {"path": str(audit_path), "sha256": _sha256(audit_path)},
            "semantic_adjudications": ledger_inputs,
            # The registry validates the canonical single-ledger path/hash as
            # well as each embedded decision.  Keep this singular descriptor
            # for that compatibility contract while retaining the plural list
            # above for provenance when callers deliberately merge ledgers.
            **({"semantic_adjudication": ledger_inputs[0]} if len(ledger_inputs) == 1 else {}),
        },
        "summary": {
            "audited_pairs": len(records),
            "semantic_queries_reviewed": len(decisions),
            "semantic_decisions": dict(sorted(decision_counts.items())),
            "reconciled_classifications": dict(sorted(classes.items())),
            "same_pair_recorded": same,
            "later_paper_recorded_pair_unconfirmed": later,
            "no_exact_doi_or_title_match": no_exact,
            "candidate_new_pair_links": later + no_exact,
            "transitions": [
                {"from": prior, "to": after, "pairs": count}
                for (prior, after), count in sorted(transitions.items())
            ],
        },
        "records": records,
    }


def write_reconciliation(payload: Mapping[str, Any], output: Path) -> None:
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
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ledger", type=Path, action="append", help="Adjudication ledger; repeat to merge disjoint ledgers")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    payload = reconcile(args.audit, args.ledger or [DEFAULT_LEDGER])
    write_reconciliation(payload, args.output)
    summary = payload["summary"]
    print(
        f"WROTE {args.output} reviewed={summary['semantic_queries_reviewed']} "
        f"same_pair={summary['same_pair_recorded']} later_only={summary['later_paper_recorded_pair_unconfirmed']} "
        f"no_exact={summary['no_exact_doi_or_title_match']} candidate_new={summary['candidate_new_pair_links']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
