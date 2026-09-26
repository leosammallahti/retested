"""Build the evidence-first Retested/FORRT reconciliation registry.

This registry is deliberately additive.  It does not replace the site's legacy
paper-pair graph and it does not pretend that a DOI pair identifies an effect,
study, sample, or analysis.  Instead it preserves four different grains:

* an exact citable expression (DOI/URL/OpenAlex/title identity);
* an ordered original/later expression pair;
* Retested's source-reviewed, report-scoped claim tests and assessments; and
* evidence-backed identity/overlap assertions.

The output is deterministic and contains no generated timestamp.  A separate
summary states whether the *structure* validates and why the comparison is not
yet assurance-complete.  In particular, an embedding result or a rejected
candidate can never become evidence that a pair is absent from FORRT.

Run with::

    python -m pipeline reconciliation-registry --check
    python -m pipeline reconciliation-registry
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .ids import norm_name
from .load import ROOT
from .pair_summaries import canonical_doi

SCHEMA_VERSION = "reconciliation-registry/v1"
GENERATOR_VERSION = 2

PAIR_SUMMARIES = ROOT / "data" / "discovery" / "pair_match_summaries.json"
PROMOTED = ROOT / "data" / "curated" / "promoted_pairs.json"
ATTEMPTS = ROOT / "data" / "build" / "attempts.json"
RECONCILED = ROOT / "data" / "curated" / "forrt_overlap_reconciled_20260926.json"
SEMANTIC_REVIEW = ROOT / "data" / "curated" / "forrt_semantic_match_review_20260926.json"
EFFECT_LEDGER = ROOT / "data" / "curated" / "registry" / "effect_ids.csv"
POLICY = ROOT / "data" / "curated" / "registry" / "reconciliation_policy_v1.json"
RAW_MANIFEST = ROOT / "data" / "raw" / "forrt" / "MANIFEST.json"
OUTPUT = ROOT / "data" / "build" / "reconciliation_registry.json"
SUMMARY_OUTPUT = ROOT / "data" / "build" / "reconciliation_registry.summary.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _id(prefix: str, *parts: object) -> str:
    body = "\0".join(str(part) for part in parts)
    # Registry IDs are new and have no compatibility obligation.  Keep the
    # full digest so a dictionary insertion cannot hide a truncated-ID clash.
    return prefix + _digest_text(body)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pair_key(row: Mapping[str, Any]) -> tuple[str, str]:
    original = canonical_doi(row.get("doi_o"))
    later = canonical_doi(row.get("doi_r") or row.get("rep_key"))
    if not original or not later:
        raise ValueError(f"missing canonical DOI pair: {row.get('doi_o')!r}, {row.get('doi_r')!r}")
    return original, later


def _title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    normalized = " ".join("".join(ch if ch.isalnum() else " " for ch in normalized).split())
    return "title-sha256:" + _digest_text(normalized)


def _identifier_key(item: Mapping[str, Any]) -> str | None:
    kind = str(item.get("kind") or "")
    value = item.get("value")
    if value in (None, ""):
        return None
    if kind == "doi":
        doi = canonical_doi(value)
        return f"doi:{doi}" if doi else None
    if kind == "url":
        return f"url:{str(value)}"
    if kind == "openalex":
        return f"openalex:{str(value).upper()}"
    if kind == "alt_identifier":
        return f"alt:{str(value).casefold()}"
    if kind == "title":
        return _title_key(str(value))
    return None


def _expression(key: str) -> dict[str, Any]:
    kind, _, value = key.partition(":")
    doi = value if kind == "doi" else None
    identity_status = {
        "doi": "exact_doi_expression",
        "url": "source_locator_identity_unresolved",
        "openalex": "external_bibliographic_record_identity_unresolved",
        "alt": "source_identifier_identity_unresolved",
        "title-candidate": "record_scoped_title_candidate_not_identity",
    }.get(kind, "unclassified_identifier_identity_unresolved")
    return {
        "id": _id("ex_", key),
        "identity_key": key,
        "identity_kind": kind,
        "identity_value": value,
        "doi": doi,
        # Only a DOI is treated as exact expression identity.  URLs, external
        # records, and titles stay retrieval/source identifiers until reviewed.
        "identity_status": identity_status,
        "work_identity_status": "not_materialized",
        "title_observations": [],
    }


def _record_scoped_key(key: str, origin: str, record_id: str, side: str) -> str:
    """Prevent a normalized title from silently becoming expression identity."""

    if key.startswith("title-sha256:"):
        digest = key.split(":", 1)[1]
        return f"title-candidate:{origin}:{record_id}:{side}:{digest}"
    return key


_STABLE_EVIDENCE_PATHS = {
    "/tmp/retested_live_forrt_extractor.csv": (
        "data/raw/forrt/snapshots/2026-09-26/flora-extractor_extracted.csv"
    ),
    "/tmp/retested_live_forrt_pending.csv": (
        "data/raw/forrt/snapshots/2026-09-26/flora-extractor_target_pending.csv"
    ),
    "/tmp/retested_live_forrt_validated.csv": (
        "data/raw/forrt/snapshots/2026-09-26/flora-validation_validated_export.csv"
    ),
    "/tmp/retested_live_forrt_flora.csv": (
        "data/raw/forrt/snapshots/2026-09-26/fred-data_output_flora.csv"
    ),
    "/tmp/retested_live_forrt_flora_filtered.csv": (
        "data/raw/forrt/snapshots/2026-09-26/fred-data_output_flora_filtered.csv"
    ),
}


def _stable_evidence_locations(
    locations: Sequence[Mapping[str, Any]], query_record_id: str | None,
) -> list[dict[str, Any]]:
    """Resolve ephemeral review locators to frozen or curated artifacts."""

    stable: list[dict[str, Any]] = []
    for raw in locations:
        item = dict(raw)
        path = str(item.get("path") or "")
        base, separator, suffix = path.partition(":")
        if base in _STABLE_EVIDENCE_PATHS:
            item["path"] = _STABLE_EVIDENCE_PATHS[base] + (separator + suffix if separator else "")
        elif path.startswith("/tmp/retested_embedding_review"):
            item.pop("path", None)
            item["path"] = "data/curated/forrt_semantic_match_review_20260926.json"
            item["record_selector"] = {"query_record_id": query_record_id}
        stable.append(item)
    return stable


def _source_layer(status: str, policy: Mapping[str, Any]) -> str:
    layers = policy.get("source_layers") or {}
    if status not in layers:
        raise ValueError(f"source status is absent from policy: {status}")
    return str(layers[status])


def _best_status(statuses: Iterable[str], policy: Mapping[str, Any]) -> str | None:
    found = set(statuses)
    for status in policy.get("membership_priority") or []:
        if status in found:
            return str(status)
    return sorted(found)[0] if found else None


def _component_texts(record: Mapping[str, Any], component: str) -> list[str]:
    return [str(item["text"]) for item in record.get("components", {}).get(component, []) if item.get("text")]


def _effect_ids(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["key"]: row["effect_id"] for row in csv.DictReader(handle)}


def _input_descriptor(path: Path) -> dict[str, Any]:
    return {"path": str(path.relative_to(ROOT)), "sha256": _sha256(path), "bytes": path.stat().st_size}


def _output_path_problems(
    output: Path, summary_output: Path, input_paths: Sequence[Path],
) -> list[str]:
    output_resolved = output.resolve()
    summary_resolved = summary_output.resolve()
    problems: list[str] = []
    if output_resolved == summary_resolved:
        problems.append("registry output and summary output resolve to the same path")
    inputs_resolved = {path.resolve() for path in input_paths}
    if output_resolved in inputs_resolved:
        problems.append(f"registry output would overwrite an input: {output}")
    if summary_resolved in inputs_resolved:
        problems.append(f"registry summary would overwrite an input: {summary_output}")
    return problems


def _manifest_problems(manifest: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    indexed = {
        f"data/raw/forrt/{entry['path']}": entry
        for entry in manifest.get("files") or []
        if entry.get("path")
    }
    problems: list[str] = []
    for expected in policy.get("pinned_current_sources") or []:
        path = str(expected["path"])
        entry = indexed.get(path)
        if entry is None:
            problems.append(f"pinned source absent from raw manifest: {path}")
            continue
        if entry.get("sha256") != expected.get("sha256"):
            problems.append(f"pinned source hash disagrees with raw manifest: {path}")
        if entry.get("source_status") != expected.get("status"):
            problems.append(f"pinned source status disagrees with raw manifest: {path}")
        if entry.get("repository_commit") != expected.get("commit"):
            problems.append(f"pinned source commit disagrees with raw manifest: {path}")
        source_path = ROOT / path
        if not source_path.exists():
            problems.append(f"pinned source file is absent: {path}")
        elif _sha256(source_path) != expected.get("sha256"):
            problems.append(f"pinned source file hash mismatch: {path}")
    return problems


def _semantic_review_problems(
    reconciled: Mapping[str, Any],
    semantic_review: Mapping[str, Any],
    semantic_review_path: Path,
) -> list[str]:
    """Verify that the reconciled ledger faithfully embeds the review artifact."""

    problems: list[str] = []
    declared = (reconciled.get("inputs") or {}).get("semantic_adjudication") or {}
    actual_sha = _sha256(semantic_review_path)
    if declared.get("sha256") != actual_sha:
        problems.append("reconciled ledger's declared semantic-review hash does not match the input artifact")
    declared_path = declared.get("path")
    if not declared_path or Path(str(declared_path)).resolve() != semantic_review_path.resolve():
        problems.append("reconciled ledger's declared semantic-review path does not match the input artifact")

    decisions = list(semantic_review.get("decisions") or [])
    decision_ids = [str(row.get("query_record_id")) for row in decisions]
    if len(decision_ids) != len(set(decision_ids)):
        problems.append("semantic-review artifact has duplicate query record IDs")
    decision_by_id = {identifier: row for identifier, row in zip(decision_ids, decisions)}
    embedded_rows = [
        (row, row.get("semantic_adjudication") or {})
        for row in reconciled.get("records") or []
        if row.get("semantic_adjudication")
    ]
    embedded_ids = [str(semantic.get("query_record_id")) for _, semantic in embedded_rows]
    if len(embedded_ids) != len(set(embedded_ids)):
        problems.append("reconciled ledger has duplicate embedded semantic query IDs")
    if set(embedded_ids) != set(decision_ids):
        problems.append("reconciled ledger does not contain exactly the semantic-review decisions")

    fields = (
        "decision", "candidate_record_ids", "original_work_matches", "later_work_matches",
        "evidence", "evidence_locations", "top_cosine_similarity",
    )
    positive_decisions = {
        "confirmed_same_pair",
        "confirmed_same_later_version_same_pair",
        "same_later_work_different_original",
    }
    for reconciled_row, embedded in embedded_rows:
        query_id = str(embedded.get("query_record_id"))
        reviewed = decision_by_id.get(query_id)
        if reviewed is None:
            continue
        if any(embedded.get(field) != reviewed.get(field) for field in fields):
            problems.append(f"embedded semantic decision differs from review artifact: {query_id}")
        if _pair_key(reconciled_row) != _pair_key(reviewed):
            problems.append(f"semantic decision DOI pair differs from reconciled record: {query_id}")
        if reviewed.get("decision") in positive_decisions and (
            not reviewed.get("candidate_record_ids")
            or not reviewed.get("evidence")
            or not reviewed.get("evidence_locations")
        ):
            problems.append(f"positive semantic decision lacks candidate/evidence linkage: {query_id}")

    summary_counts = ((semantic_review.get("summary") or {}).get("counts") or {})
    actual_counts = Counter(str(row.get("decision")) for row in decisions)
    if summary_counts and any(
        int(summary_counts.get(label, 0)) != int(actual_counts.get(label, 0))
        for label in set(summary_counts) | set(actual_counts)
    ):
        problems.append("semantic-review summary counts do not match its decision records")
    return problems


def build_registry(
    summaries: Mapping[str, Any],
    promoted: Sequence[Mapping[str, Any]],
    attempts: Mapping[str, Mapping[str, Any]],
    reconciled: Mapping[str, Any],
    effect_ids: Mapping[str, str],
    policy: Mapping[str, Any],
    *,
    inputs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic registry document from already loaded inputs."""

    query_records = list(summaries.get("query_records") or [])
    corpus_records = list(summaries.get("corpus_records") or [])
    source_stats = list(summaries.get("sources") or [])
    if not query_records or not corpus_records or not source_stats:
        raise ValueError("pair summary needs query_records, corpus_records, and sources")

    snapshots: dict[tuple[str, str], dict[str, Any]] = {}
    for source in source_stats:
        status = str(source["status"])
        path = str(source["path"])
        snapshot_key = (str(source["source"]), path)
        if snapshot_key in snapshots:
            raise ValueError(f"duplicate source snapshot descriptor: {snapshot_key}")
        snapshot_id = _id("sn_", source["source"], path, source.get("sha256") or "")
        snapshots[snapshot_key] = {
            "id": snapshot_id,
            "source_name": source["source"],
            "status": status,
            "layer": _source_layer(status, policy),
            "path": path,
            "sha256": source.get("sha256"),
            "rows_read": source.get("rows_read"),
            "rows_indexed": source.get("rows_indexed"),
            "pair_references": source.get("pair_references"),
            "later_status_references": source.get("later_status_references"),
        }

    expressions: dict[str, dict[str, Any]] = {}
    title_sets: dict[str, set[str]] = defaultdict(set)

    def expression_id(key: str) -> str:
        if key not in expressions:
            expressions[key] = _expression(key)
        return str(expressions[key]["id"])

    pairs: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    summary_records: dict[str, dict[str, Any]] = {}
    seen_origin_record_ids: set[tuple[str, str]] = set()
    corpus_record_by_id: dict[str, Mapping[str, Any]] = {}
    query_by_pair: dict[tuple[str, str], Mapping[str, Any]] = {}
    aliases: dict[str, dict[str, Any]] = {}
    later_status_records: list[dict[str, Any]] = []

    def add_alias(primary_key: str, alias_key: str, record: Mapping[str, Any], side: str) -> None:
        if primary_key == alias_key:
            return
        left, right = sorted((expression_id(primary_key), expression_id(alias_key)))
        evidence = sorted(str(item["id"]) for item in record.get("provenance") or [])
        alias_id = _id("wa_", "source_asserted_identifier_alias", left, right, *evidence)
        aliases[alias_id] = {
            "id": alias_id,
            "predicate": "source_asserted_identifier_alias",
            "expression_ids": [left, right],
            "side": side,
            "review_status": "source_reported_not_curator_merged",
            "evidence_provenance_ids": evidence,
        }

    def add_record(record: Mapping[str, Any], origin: str) -> None:
        upstream_record_id = str(record["record_id"])
        origin_record_key = (origin, upstream_record_id)
        if origin_record_key in seen_origin_record_ids:
            raise ValueError(f"duplicate {origin} summary record id: {upstream_record_id}")
        seen_origin_record_ids.add(origin_record_key)
        if origin == "forrt":
            corpus_record_by_id[upstream_record_id] = record
        summary_record_id = _id("sr_", origin, upstream_record_id)
        raw_original_key = record.get("original_key")
        raw_later_key = str(record["replication_key"])
        original_key = (
            _record_scoped_key(str(raw_original_key), origin, upstream_record_id, "original")
            if raw_original_key else None
        )
        later_key = _record_scoped_key(raw_later_key, origin, upstream_record_id, "replication")
        later_expression_id = expression_id(later_key)
        pair_id = None
        if original_key:
            original_expression_id = expression_id(str(original_key))
            pair_id = _id("pr_", original_expression_id, "later", later_expression_id)
            pair = pairs.setdefault(
                pair_id,
                {
                    "id": pair_id,
                    "original_expression_id": original_expression_id,
                    "later_expression_id": later_expression_id,
                    "expression_pair_scope": (
                        "source_reported_same_expression_anomaly"
                        if original_expression_id == later_expression_id
                        else "distinct_expressions"
                    ),
                    "requires_identity_review": original_expression_id == later_expression_id,
                    "retested_summary_record_ids": [],
                    "forrt_summary_record_ids": [],
                    "source_observation_ids": [],
                    "forrt_statuses": [],
                    "best_forrt_membership_status": None,
                },
            )
            target = "retested_summary_record_ids" if origin == "retested" else "forrt_summary_record_ids"
            pair[target].append(summary_record_id)
            if origin == "retested":
                if _pair_key(record) in query_by_pair:
                    raise ValueError(f"duplicate normalized Retested query pair: {_pair_key(record)}")
                query_by_pair[_pair_key(record)] = record
        else:
            original_expression_id = None

        summary_payload = {
            "upstream_summary_record_id": upstream_record_id,
            "origin": origin,
            "record_kind": record["record_kind"],
            "doi_o": record.get("doi_o"),
            "doi_r": record.get("doi_r"),
            "original_key_reported": raw_original_key,
            "later_key_reported": raw_later_key,
            "identifiers": record.get("identifiers") or {},
            "components": record.get("components") or {},
            "identity_text": record.get("identity_text"),
            "match_summary": record.get("match_summary"),
            "match_summary_components": record.get("match_summary_components") or [],
            "missing_components": record.get("missing_components") or [],
            "observed_result": record.get("observed_result"),
            "outcome_labels": record.get("outcome_labels") or [],
            "upstream_provenance_ids": sorted(
                str(item["id"]) for item in record.get("provenance") or []
            ),
        }
        summary_records[summary_record_id] = {
            "id": summary_record_id,
            **summary_payload,
            "original_expression_id": original_expression_id,
            "later_expression_id": later_expression_id,
            "pair_id": pair_id,
            "payload_sha256": _digest_text(json.dumps(summary_payload, ensure_ascii=False, sort_keys=True)),
        }

        for side, primary in (("original", original_key), ("replication", later_key)):
            if not primary:
                continue
            component = "original_title" if side == "original" else "replication_title"
            for title in _component_texts(record, component):
                title_sets[str(primary)].add(title)
            for item in record.get("identifiers", {}).get(side, []):
                alias_key = _identifier_key(item)
                if alias_key:
                    alias_key = _record_scoped_key(
                        alias_key, origin, upstream_record_id, side,
                    )
                    add_alias(str(primary), alias_key, record, side)

        record_observations = []
        for provenance in record.get("provenance") or []:
            source_key = (str(provenance["source"]), str(provenance["path"]))
            snapshot = snapshots.get(source_key)
            if snapshot is None:
                raise ValueError(f"provenance has no source snapshot: {source_key}")
            observation_id = _id("ob_", snapshot["id"], provenance["row"], summary_record_id)
            if observation_id in observations:
                raise ValueError(f"duplicate source observation id: {observation_id}")
            observation = {
                "id": observation_id,
                "snapshot_id": snapshot["id"],
                "summary_record_id": summary_record_id,
                "source_provenance_id": provenance["id"],
                "source_row": provenance["row"],
                "pair_id": pair_id,
                "original_expression_id": original_expression_id,
                "later_expression_id": later_expression_id,
                "record_kind": record["record_kind"],
            }
            observations[observation_id] = observation
            record_observations.append(observation_id)
            if pair_id and origin == "forrt":
                pairs[pair_id]["forrt_statuses"].append(snapshot["status"])
        if pair_id:
            pairs[pair_id]["source_observation_ids"].extend(record_observations)
        else:
            later_status_records.append({
                "summary_record_id": summary_record_id,
                "later_expression_id": later_expression_id,
                "source_observation_ids": sorted(record_observations),
            })

    for record in query_records:
        add_record(record, "retested")
    for record in corpus_records:
        add_record(record, "forrt")

    for key, titles in title_sets.items():
        expressions[key]["title_observations"] = sorted(titles)
    for pair in pairs.values():
        pair["retested_summary_record_ids"] = sorted(set(pair["retested_summary_record_ids"]))
        pair["forrt_summary_record_ids"] = sorted(set(pair["forrt_summary_record_ids"]))
        pair["source_observation_ids"] = sorted(set(pair["source_observation_ids"]))
        pair["forrt_statuses"] = sorted(set(pair["forrt_statuses"]))
        pair["best_forrt_membership_status"] = _best_status(pair["forrt_statuses"], policy)

    # Reviewed same-work/version assertions remain edges.  V1 never changes an
    # expression ID or silently picks a canonical version-family representative.
    reviewed_work_assertions: dict[str, dict[str, Any]] = {}
    reviewed_assertion_ids_by_query: dict[str, list[str]] = defaultdict(list)
    reconciled_by_pair: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in reconciled.get("records") or []:
        key = _pair_key(row)
        if key in reconciled_by_pair:
            raise ValueError(f"duplicate reconciled DOI pair: {key}")
        reconciled_by_pair[key] = row
        semantic = row.get("semantic_adjudication") or {}
        positive_decisions = {
            "confirmed_same_pair",
            "confirmed_same_later_version_same_pair",
            "same_later_work_different_original",
        }
        if semantic and semantic.get("query_record_id") != (query_by_pair.get(key) or {}).get("record_id"):
            raise ValueError(f"semantic query linkage disagrees with Retested summary record: {key}")
        missing_candidates = set(semantic.get("candidate_record_ids") or []) - set(corpus_record_by_id)
        if semantic.get("decision") in positive_decisions and missing_candidates:
            raise ValueError(
                f"positive semantic decision references missing frozen candidates: {sorted(missing_candidates)}"
            )
        candidates = [
            corpus_record_by_id[cid]
            for cid in semantic.get("candidate_record_ids") or []
            if cid in corpus_record_by_id
        ]
        query = query_by_pair.get(key)
        if not query:
            continue
        for side, matches in (("original", semantic.get("original_work_matches")), ("replication", semantic.get("later_work_matches"))):
            if matches is not True:
                continue
            query_key = _record_scoped_key(
                str(query["original_key" if side == "original" else "replication_key"]),
                "retested", str(query["record_id"]), side,
            )
            for candidate in candidates:
                candidate_key = candidate.get("original_key" if side == "original" else "replication_key")
                if not candidate_key:
                    continue
                candidate_key = _record_scoped_key(
                    str(candidate_key), "forrt", str(candidate["record_id"]), side,
                )
                left, right = sorted((expression_id(str(query_key)), expression_id(str(candidate_key))))
                if left == right:
                    continue
                assertion_id = _id("wa_", "reviewed_same_work", side, left, right, semantic.get("query_record_id"))
                reviewed_work_assertions[assertion_id] = {
                    "id": assertion_id,
                    "predicate": "reviewed_same_work",
                    "expression_ids": [left, right],
                    "side": side,
                    "review_status": "source_adjudicated_single_review",
                    "decision": semantic.get("decision"),
                    "evidence": semantic.get("evidence"),
                    "evidence_locations": _stable_evidence_locations(
                        semantic.get("evidence_locations") or [], semantic.get("query_record_id"),
                    ),
                    "review_artifact": "data/curated/forrt_semantic_match_review_20260926.json",
                    "query_record_id": semantic.get("query_record_id"),
                    "candidate_record_id": candidate.get("record_id"),
                }
                reviewed_assertion_ids_by_query[str(semantic.get("query_record_id"))].append(assertion_id)

    # Retested's rows support scoped claims and outcomes, but generally do not
    # support stable Study or Sample identities.  Preserve every reviewed row.
    claims: dict[str, dict[str, Any]] = {}
    effects: dict[str, dict[str, Any]] = {}
    tests: dict[str, dict[str, Any]] = {}
    assessments: list[dict[str, Any]] = []
    promoted_pair_rows: dict[tuple[str, str], list[int]] = defaultdict(list)
    observation_by_promoted_row: dict[int, str] = {}
    snapshots_by_id = {snapshot["id"]: snapshot for snapshot in snapshots.values()}
    for observation in observations.values():
        snapshot = snapshots_by_id[observation["snapshot_id"]]
        if snapshot["layer"] == "retested_reviewed" and snapshot["path"].endswith("promoted_pairs.json"):
            try:
                observation_by_promoted_row[int(observation["source_row"])] = observation["id"]
            except (TypeError, ValueError):
                pass

    for row_number, row in enumerate(promoted, 1):
        original_doi, later_doi = _pair_key(row)
        promoted_pair_rows[(original_doi, later_doi)].append(row_number)
        original_expression_id = expression_id(f"doi:{original_doi}")
        later_expression_id = expression_id(f"doi:{later_doi}")
        effect_key = norm_name(str(row["effect_name"]))
        effect_id = effect_ids.get(effect_key)
        if not effect_id:
            raise ValueError(f"promoted row {row_number} effect absent from ledger: {row['effect_name']}")
        source_observation_id = observation_by_promoted_row.get(row_number)
        if not source_observation_id:
            raise ValueError(f"promoted row {row_number} has no source observation")
        effect = effects.setdefault(effect_id, {
            "id": effect_id,
            "identity_authority": "legacy_append_only_name_ledger",
            "identity_limit": "editorial effect cluster; not sufficient claim/study identity",
            "labels": [],
            "claim_ids": [],
        })
        effect["labels"].append(str(row["effect_name"]))

        # A reviewed source row is the strongest identity available here.  Do
        # not merge claims merely because an editorial effect label and paper
        # happen to match: one paper can contain several estimands or studies.
        claim_id = _id("cl_", "retested_source_claim", source_observation_id)
        claim = claims.setdefault(claim_id, {
            "id": claim_id,
            "effect_id": effect_id,
            "original_expression_id": original_expression_id,
            "study_id": None,
            "identity_status": "source_scoped_claim_not_canonicalized",
            "scope_status": "source_row_claim_study_and_estimand_unresolved",
            "labels": [],
            "claim_texts": [],
            "claim_quotes": [],
            "source_observation_ids": [],
        })
        effect["claim_ids"].append(claim_id)
        claim["labels"].append(str(row["effect_name"]))
        claim["claim_texts"].append(str(row["effect_claim"]))
        claim["claim_quotes"].append({
            "text": row["effect_claim_quote"],
            "source_url": row["original_source_url"],
            "source_observation_id": source_observation_id,
        })
        claim["source_observation_ids"].append(source_observation_id)

        test_id = _id("ct_", claim_id, later_expression_id)
        test = tests.setdefault(test_id, {
            "id": test_id,
            "claim_id": claim_id,
            "original_expression_id": original_expression_id,
            "later_expression_id": later_expression_id,
            "replication_study_id": None,
            "sample_ids": [],
            "scope_status": "report_scoped_study_and_sample_unresolved",
            "relation_kind": "replication",
            "target_assertions": [],
            "assessment_ids": [],
        })
        test["target_assertions"].append({
            "text": row["replication_target_quote"],
            "source_url": row["replication_source_url"],
            "source_observation_id": source_observation_id,
        })
        assessment_id = _id("ra_", test_id, source_observation_id)
        assessment = {
            "id": assessment_id,
            "claim_test_id": test_id,
            "result_id": None,
            "result_scope_status": "report_scoped_contrast_identity_unresolved",
            "outcome": row["outcome"],
            "outcome_quote": row["outcome_quote"],
            "outcome_quote_source": row["outcome_quote_source"],
            "replication_source_url": row["replication_source_url"],
            "review_note": row.get("review_note"),
            "reviewed_by": row["reviewed_by"],
            "reviewed_on": row["reviewed_on"],
            "source_observation_id": source_observation_id,
        }
        assessments.append(assessment)
        test["assessment_ids"].append(assessment_id)

    for collection in (effects, claims, tests):
        for record in collection.values():
            for field in (
                "labels", "claim_ids", "claim_texts", "claim_quotes", "source_observation_ids",
                "target_assertions", "assessment_ids",
            ):
                if field in record:
                    if field in {"claim_quotes", "target_assertions"}:
                        unique = {json.dumps(item, ensure_ascii=False, sort_keys=True): item for item in record[field]}
                        record[field] = [unique[key] for key in sorted(unique)]
                    else:
                        record[field] = sorted(set(record[field]))

    # Map the built Retested layer to canonical expression pairs.  This is a
    # bibliographic comparison only; every effect/study axis stays unreviewed.
    built_by_pair: dict[tuple[str, str], Mapping[str, Any]] = {}
    for attempt in attempts.values():
        if "retested" not in (attempt.get("sources") or []):
            continue
        key = _pair_key(attempt)
        if key in built_by_pair:
            raise ValueError(f"duplicate built Retested pair after normalization: {key}")
        built_by_pair[key] = attempt

    addition_pairs = {
        key for key, attempt in built_by_pair.items()
        if set(attempt.get("sources") or []) == {"retested"}
    }
    overlay_pairs = set(built_by_pair) - addition_pairs
    if set(reconciled_by_pair) != addition_pairs:
        raise ValueError(
            f"reconciled/build addition mismatch: reconciled={len(reconciled_by_pair)} additions={len(addition_pairs)}"
        )

    forrt_original_expressions = {
        pair["original_expression_id"]
        for pair in pairs.values()
        if pair["forrt_summary_record_ids"]
    }

    def reconciliation_reference(rec: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if rec is None:
            return None
        semantic = rec.get("semantic_adjudication") or {}
        semantic_reference = None
        if semantic:
            semantic_reference = {
                "decision": semantic.get("decision"),
                "query_record_id": semantic.get("query_record_id"),
                "candidate_record_ids": semantic.get("candidate_record_ids") or [],
                "original_work_matches": semantic.get("original_work_matches"),
                "later_work_matches": semantic.get("later_work_matches"),
                "evidence": semantic.get("evidence"),
                "evidence_locations": _stable_evidence_locations(
                    semantic.get("evidence_locations") or [], semantic.get("query_record_id"),
                ),
                "review_artifact": "data/curated/forrt_semantic_match_review_20260926.json",
                "top_cosine_similarity_retrieval_only": semantic.get("top_cosine_similarity"),
                "independent_work_identity_review": semantic.get("independent_work_identity_review"),
            }
        return {
            "artifact": "data/curated/forrt_overlap_reconciled_20260926.json",
            "record_key": {"doi_o": rec.get("doi_o"), "doi_r": rec.get("doi_r")},
            "classification": rec.get("classification"),
            "combined_classification": rec.get("combined_classification"),
            "reconciled_classification": rec.get("reconciled_classification"),
            "semantic_adjudication": semantic_reference,
        }

    overlaps: list[dict[str, Any]] = []
    for key in sorted(built_by_pair):
        original_doi, later_doi = key
        original_expression_id = expression_id(f"doi:{original_doi}")
        later_expression_id = expression_id(f"doi:{later_doi}")
        pair_id = _id("pr_", original_expression_id, "later", later_expression_id)
        attempt = built_by_pair[key]
        rec = reconciled_by_pair.get(key)
        basis: list[str] = []
        review_requirements = ["effect_identity", "replication_study_identity", "sample_independence"]
        pair = pairs[pair_id]
        exact_forrt_pair_reported = bool(pair["forrt_summary_record_ids"])
        semantic = (rec or {}).get("semantic_adjudication") or {}
        decision = semantic.get("decision")
        independent = semantic.get("independent_work_identity_review") or {}
        independent_status = independent.get("second_review_status")
        if exact_forrt_pair_reported:
            relation = "exact_expression_pair_reported"
            assurance_status = "exact_normalized_doi_pair_in_frozen_forrt_source"
            basis.append("a frozen FORRT source reports the same normalized original and later DOI pair")
        elif decision == "confirmed_same_later_version_same_pair":
            relation = "reviewed_same_work_pair_versioned_expressions"
            basis.append("source review links both works through different report versions or identifiers")
            if independent_status == "agree":
                assurance_status = "independently_confirmed_positive_work_identity"
                basis.append("an independent reviewer agreed on ordered bibliographic Work identity")
            elif independent_status == "agree_with_evidence_gap":
                assurance_status = "independently_confirmed_work_identity_with_provenance_gap"
                basis.append("an independent reviewer agreed but recorded a material provenance gap")
                review_requirements.append("work_identity_provenance_gap")
            else:
                assurance_status = "single_review_positive_work_identity"
                review_requirements.append("independent_work_identity_adjudication")
        elif decision == "confirmed_same_pair":
            relation = "reviewed_same_work_pair_expression_unresolved"
            basis.append("source review identifies the same two works but the FORRT expression pair is incomplete")
            if independent_status == "agree":
                assurance_status = "independently_confirmed_positive_work_identity"
                basis.append("an independent reviewer agreed on ordered bibliographic Work identity")
            elif independent_status == "agree_with_evidence_gap":
                assurance_status = "independently_confirmed_work_identity_with_provenance_gap"
                basis.append("an independent reviewer agreed but recorded a material provenance gap")
                review_requirements.append("work_identity_provenance_gap")
            else:
                assurance_status = "single_review_positive_work_identity"
                review_requirements.append("independent_work_identity_adjudication")
        elif rec and rec.get("reconciled_classification") == "same_pair_recorded":
            relation = "title_or_alternate_identifier_pair_candidate"
            assurance_status = "candidate_not_identity_assertion"
            basis.append("a prior audit linked the title or an alternate identifier, without source adjudication")
            review_requirements.append("work_identity_source_review")
        elif key in overlay_pairs:
            # This should normally be unreachable: a built overlay ought to be
            # represented by an exact frozen FORRT pair observation.
            relation = "legacy_overlay_not_reproduced_in_frozen_sources"
            assurance_status = "legacy_positive_requires_reconciliation"
            basis.append("the legacy build labels an overlay but the frozen registry has no exact pair record")
            review_requirements.append("legacy_overlay_reconciliation")
        else:
            assert rec is not None
            klass = rec["reconciled_classification"]
            if decision == "same_later_work_different_original":
                relation = "reviewed_same_later_work_different_original"
                assurance_status = "single_review_positive_later_work_identity"
                basis.append("source adjudication confirms the later work and a different FORRT original")
                review_requirements.append("independent_work_identity_adjudication")
            elif klass == "later_paper_recorded_pair_unconfirmed":
                relation = "later_work_reported_original_relation_unresolved"
                assurance_status = "later_work_presence_only"
                basis.append("later work is recorded but its original-work relation is unresolved")
                review_requirements.append("original_work_identity")
            elif original_expression_id in forrt_original_expressions:
                relation = "original_expression_reported_with_other_later"
                assurance_status = "original_expression_presence_only"
                basis.append("original DOI occurs in a different retained FORRT pair; later work is not identified")
                review_requirements.append("bounded_no_match_coverage")
            elif semantic.get("original_work_matches") is True:
                relation = "reviewed_original_work_in_pending_record"
                assurance_status = "single_review_original_work_identity_only"
                basis.append("source review links the original only through a pending/unidentified-original record")
                review_requirements.extend(["structured_original_link", "bounded_no_match_coverage"])
            else:
                relation = "not_fully_compared"
                assurance_status = "no_positive_identity_relation_complete_coverage_absent"
                basis.append("no positive work identity is established and required comparison blocks remain incomplete")
                review_requirements.append("bounded_no_match_coverage")
        overlaps.append({
            "query_pair_id": pair_id,
            "doi_o": original_doi,
            "doi_r": later_doi,
            "legacy_attempt_id": attempt["id"],
            "built_stratum": "forrt_overlay" if key in overlay_pairs else "retested_addition",
            "bibliographic_relation": relation,
            "effect_relation": "not_compared",
            "study_relation": "not_compared",
            "sample_relation": "not_compared",
            "outcome_relation": "not_compared",
            "assurance_status": assurance_status,
            "basis": basis,
            "review_requirements": sorted(set(review_requirements)),
            "work_identity_assertion_ids": sorted(
                reviewed_assertion_ids_by_query.get(str(semantic.get("query_record_id")), [])
            ),
            "reconciliation_reference": reconciliation_reference(rec),
        })

    relation_counts = Counter(item["bibliographic_relation"] for item in overlaps)
    addition_relation_counts = Counter(
        item["bibliographic_relation"]
        for item in overlaps
        if item["built_stratum"] == "retested_addition"
    )
    semantic_rows = [
        row.get("semantic_adjudication") or {}
        for row in reconciled_by_pair.values()
        if row.get("semantic_adjudication")
    ]
    semantic_missing_rationale = sum(not row.get("evidence") for row in semantic_rows)
    semantic_missing_locations = sum(not row.get("evidence_locations") for row in semantic_rows)
    semantic_incomplete_evidence = sum(
        not row.get("evidence") or not row.get("evidence_locations") for row in semantic_rows
    )
    independent_reviews = [
        row["independent_work_identity_review"]
        for row in semantic_rows
        if isinstance(row.get("independent_work_identity_review"), Mapping)
    ]
    independent_status_counts = Counter(
        str(row.get("second_review_status")) for row in independent_reviews
    )
    pair_collisions = [
        {"doi_o": key[0], "doi_r": key[1], "promoted_rows": row_numbers}
        for key, row_numbers in sorted(promoted_pair_rows.items()) if len(row_numbers) > 1
    ]

    comparison_blocks = {
        "direct_pair_join": "complete",
        "one_side_identifier_joins": "complete",
        "pinned_alias_version_graph": "partial",
        "bibliographic_fallback": "partial",
        "text_semantic_retrieval": "partial",
        "textless_metadata_audit": "partial",
        "source_stratum_deduplication": "complete",
        "independent_review_and_adjudication": "partial" if independent_reviews else "not_started",
    }
    assurance_blockers = [
        "effect identity has not been compared for any paper-pair overlap",
        "study and sample identities are intentionally unresolved for imported report-scoped tests",
        "semantic review does not cover every non-exact query",
        "independent dual review and adjudication have not been completed",
    ]
    if semantic_incomplete_evidence:
        assurance_blockers.append(
            f"{semantic_incomplete_evidence} semantic decisions have incomplete evidence "
            f"({semantic_missing_rationale} lack rationale; {semantic_missing_locations} lack locations)"
        )

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "scope": policy["scope"],
        "inputs": list(inputs or []),
        "source_snapshots": sorted(snapshots.values(), key=lambda item: item["id"]),
        "expressions": sorted(expressions.values(), key=lambda item: item["id"]),
        "work_identity_assertions": sorted(
            [*aliases.values(), *reviewed_work_assertions.values()], key=lambda item: item["id"]
        ),
        "source_summary_records": sorted(summary_records.values(), key=lambda item: item["id"]),
        "pairs": sorted(pairs.values(), key=lambda item: item["id"]),
        "source_observations": sorted(observations.values(), key=lambda item: item["id"]),
        "later_status_records": sorted(later_status_records, key=lambda item: item["summary_record_id"]),
        "effects": sorted(effects.values(), key=lambda item: item["id"]),
        "claims": sorted(claims.values(), key=lambda item: item["id"]),
        "studies": [],
        "samples": [],
        "claim_tests": sorted(tests.values(), key=lambda item: item["id"]),
        "result_assessments": sorted(assessments, key=lambda item: item["id"]),
        "overlap_decisions": overlaps,
        "coverage": {
            "comparison_state": "interim_partially_source_adjudicated",
            "comparison_blocks": comparison_blocks,
            "assurance_complete": False,
            "assurance_blockers": assurance_blockers,
            "semantic_queries_reviewed": len(semantic_rows),
            "semantic_decisions_incomplete_evidence": semantic_incomplete_evidence,
            "semantic_decisions_missing_rationale": semantic_missing_rationale,
            "semantic_decisions_missing_locations": semantic_missing_locations,
            "independent_work_identity_reviews": len(independent_reviews),
            "independent_work_identity_full_agreements": independent_status_counts.get("agree", 0),
            "independent_work_identity_agreements_with_evidence_gap": independent_status_counts.get("agree_with_evidence_gap", 0),
            "independent_work_identity_disagreements": independent_status_counts.get("disagree", 0),
            "promoted_normalized_pair_collisions": pair_collisions,
        },
        "counts": {
            "retested_reviewed_source_rows": len(promoted),
            "retested_normalized_pairs": len(built_by_pair),
            "retested_built_overlays": len(overlay_pairs),
            "retested_additions": len(addition_pairs),
            "forrt_summary_records": len(corpus_records),
            "forrt_pair_records": sum(record.get("record_kind") == "pair" for record in corpus_records),
            "forrt_later_status_records": sum(record.get("record_kind") == "later_paper_status" for record in corpus_records),
            "expressions": len(expressions),
            "reported_expression_relations": len(pairs),
            "distinct_expression_relations": sum(
                pair["expression_pair_scope"] == "distinct_expressions" for pair in pairs.values()
            ),
            "source_observations": len(observations),
            "source_summary_records": len(summary_records),
            "source_outcome_labels": sum(
                len(record.get("outcome_labels") or []) for record in summary_records.values()
            ),
            "effect_refs": len(effects),
            "source_scoped_claims": len(claims),
            "report_scoped_claim_tests": len(tests),
            "result_assessments": len(assessments),
            "source_reported_same_expression_anomalies": sum(
                pair["expression_pair_scope"] == "source_reported_same_expression_anomaly"
                for pair in pairs.values()
            ),
            "studies_resolved": 0,
            "samples_resolved": 0,
            "bibliographic_relations": dict(sorted(relation_counts.items())),
            "retested_addition_bibliographic_relations": dict(sorted(addition_relation_counts.items())),
            "effect_relations_resolved": 0,
            "certified_new_to_forrt": 0,
        },
    }
    return document


def validate_registry(document: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    """Return structural errors.  Assurance blockers are data, not failures."""

    problems: list[str] = []
    if document.get("schema_version") != SCHEMA_VERSION:
        problems.append("wrong schema version")

    tables = (
        "source_snapshots", "expressions", "work_identity_assertions", "source_summary_records",
        "pairs", "source_observations", "effects", "claims", "claim_tests", "result_assessments",
        "overlap_decisions",
    )
    indexes: dict[str, dict[str, Mapping[str, Any]]] = {}
    for table in tables:
        rows = document.get(table)
        if not isinstance(rows, list):
            problems.append(f"{table} is not a list")
            continue
        if table == "overlap_decisions":
            ids = [str(row.get("query_pair_id")) for row in rows]
        else:
            ids = [str(row.get("id")) for row in rows]
        if len(ids) != len(set(ids)):
            problems.append(f"{table} has duplicate ids")
        indexes[table] = {identifier: row for identifier, row in zip(ids, rows)}

    snapshot_ids = set(indexes.get("source_snapshots", {}))
    expression_ids = set(indexes.get("expressions", {}))
    summary_record_ids = set(indexes.get("source_summary_records", {}))
    pair_ids = set(indexes.get("pairs", {}))
    observation_ids = set(indexes.get("source_observations", {}))
    claim_ids = set(indexes.get("claims", {}))
    test_ids = set(indexes.get("claim_tests", {}))
    assessment_ids = set(indexes.get("result_assessments", {}))
    provenance_ids_by_summary: dict[str, set[str]] = defaultdict(set)
    for observation in document.get("source_observations") or []:
        provenance_ids_by_summary[str(observation.get("summary_record_id"))].add(
            str(observation.get("source_provenance_id"))
        )

    for snapshot in document.get("source_snapshots") or []:
        path = str(snapshot.get("path") or "")
        if path.startswith("/tmp"):
            problems.append(f"ephemeral source path: {path}")
        if not snapshot.get("sha256"):
            problems.append(f"source snapshot lacks sha256: {snapshot.get('id')}")
    pinned = {entry["path"]: entry for entry in policy.get("pinned_current_sources") or []}
    actual = {snapshot["path"]: snapshot for snapshot in document.get("source_snapshots") or []}
    for path, expected in pinned.items():
        snapshot = actual.get(path)
        if snapshot is None:
            problems.append(f"pinned current source absent: {path}")
        elif snapshot.get("sha256") != expected["sha256"] or snapshot.get("status") != expected["status"]:
            problems.append(f"pinned current source disagrees with policy: {path}")

    for expression in document.get("expressions") or []:
        if expression.get("work_identity_status") != "not_materialized":
            problems.append(f"v1 expression improperly materializes a work family: {expression.get('id')}")
        expected_identity_status = {
            "doi": "exact_doi_expression",
            "url": "source_locator_identity_unresolved",
            "openalex": "external_bibliographic_record_identity_unresolved",
            "alt": "source_identifier_identity_unresolved",
            "title-candidate": "record_scoped_title_candidate_not_identity",
        }.get(expression.get("identity_kind"), "unclassified_identifier_identity_unresolved")
        if expression.get("identity_status") != expected_identity_status:
            problems.append(f"expression has inconsistent identity status: {expression.get('id')}")
        if str(expression.get("identity_key") or "").startswith("title-sha256:"):
            problems.append(f"bare normalized title was materialized as global identity: {expression.get('id')}")
    for assertion in document.get("work_identity_assertions") or []:
        if set(assertion.get("expression_ids") or []) - expression_ids:
            problems.append(f"work assertion references missing expression: {assertion.get('id')}")
        if assertion.get("predicate") == "reviewed_same_work":
            if not assertion.get("evidence") or not assertion.get("evidence_locations"):
                problems.append(f"reviewed work assertion lacks evidence: {assertion.get('id')}")
    for record in document.get("source_summary_records") or []:
        if record.get("later_expression_id") not in expression_ids:
            problems.append(f"summary record references missing later expression: {record.get('id')}")
        if record.get("original_expression_id") is not None and record.get("original_expression_id") not in expression_ids:
            problems.append(f"summary record references missing original expression: {record.get('id')}")
        if record.get("pair_id") is not None and record.get("pair_id") not in pair_ids:
            problems.append(f"summary record references missing pair: {record.get('id')}")
        if not record.get("payload_sha256"):
            problems.append(f"summary record lacks payload hash: {record.get('id')}")
        reported_provenance = set(record.get("upstream_provenance_ids") or [])
        if reported_provenance != provenance_ids_by_summary.get(str(record.get("id")), set()):
            problems.append(f"summary record provenance does not match observations: {record.get('id')}")
        if not isinstance(record.get("outcome_labels"), list):
            problems.append(f"summary record outcome labels are not a list: {record.get('id')}")
        for label in record.get("outcome_labels") or []:
            if set(label.get("provenance_ids") or []) - reported_provenance:
                problems.append(f"summary outcome label lacks source provenance: {record.get('id')}")
    for pair in document.get("pairs") or []:
        if pair.get("original_expression_id") not in expression_ids or pair.get("later_expression_id") not in expression_ids:
            problems.append(f"pair references missing expression: {pair.get('id')}")
        same_expression = pair.get("original_expression_id") == pair.get("later_expression_id")
        expected_scope = "source_reported_same_expression_anomaly" if same_expression else "distinct_expressions"
        if pair.get("expression_pair_scope") != expected_scope:
            problems.append(f"pair has inconsistent expression scope: {pair.get('id')}")
        if bool(pair.get("requires_identity_review")) != same_expression:
            problems.append(f"pair has inconsistent identity-review flag: {pair.get('id')}")
        if set(pair.get("retested_summary_record_ids") or []) - summary_record_ids:
            problems.append(f"pair references missing Retested summary record: {pair.get('id')}")
        if set(pair.get("forrt_summary_record_ids") or []) - summary_record_ids:
            problems.append(f"pair references missing FORRT summary record: {pair.get('id')}")
        if set(pair.get("source_observation_ids") or []) - observation_ids:
            problems.append(f"pair references missing observation: {pair.get('id')}")
    for observation in document.get("source_observations") or []:
        if observation.get("snapshot_id") not in snapshot_ids:
            problems.append(f"observation references missing snapshot: {observation.get('id')}")
        if observation.get("summary_record_id") not in summary_record_ids:
            problems.append(f"observation references missing summary record: {observation.get('id')}")
        if observation.get("later_expression_id") not in expression_ids:
            problems.append(f"observation references missing later expression: {observation.get('id')}")
        if observation.get("pair_id") is not None and observation.get("pair_id") not in pair_ids:
            problems.append(f"observation references missing pair: {observation.get('id')}")
    for claim in document.get("claims") or []:
        if claim.get("original_expression_id") not in expression_ids:
            problems.append(f"claim references missing expression: {claim.get('id')}")
        if claim.get("study_id") is not None:
            problems.append(f"v1 claim fabricates study identity: {claim.get('id')}")
        if claim.get("identity_status") != "source_scoped_claim_not_canonicalized":
            problems.append(f"v1 claim improperly asserts canonical identity: {claim.get('id')}")
        if set(claim.get("source_observation_ids") or []) - observation_ids:
            problems.append(f"claim references missing source observation: {claim.get('id')}")
    for test in document.get("claim_tests") or []:
        if test.get("claim_id") not in claim_ids:
            problems.append(f"claim test references missing claim: {test.get('id')}")
        if test.get("later_expression_id") not in expression_ids:
            problems.append(f"claim test references missing later expression: {test.get('id')}")
        if test.get("replication_study_id") is not None or test.get("sample_ids"):
            problems.append(f"v1 claim test fabricates study/sample identity: {test.get('id')}")
        if set(test.get("assessment_ids") or []) - assessment_ids:
            problems.append(f"claim test references missing assessment: {test.get('id')}")
    for assessment in document.get("result_assessments") or []:
        if assessment.get("claim_test_id") not in test_ids:
            problems.append(f"assessment references missing claim test: {assessment.get('id')}")
        if assessment.get("result_id") is not None:
            problems.append(f"v1 assessment fabricates contrast result identity: {assessment.get('id')}")
        if assessment.get("source_observation_id") not in observation_ids:
            problems.append(f"assessment references missing source observation: {assessment.get('id')}")

    allowed_relations = set(policy.get("bibliographic_relations") or [])
    overlaps = document.get("overlap_decisions") or []
    for overlap in overlaps:
        if overlap.get("query_pair_id") not in pair_ids:
            problems.append(f"overlap references missing pair: {overlap.get('query_pair_id')}")
        if overlap.get("bibliographic_relation") not in allowed_relations:
            problems.append(f"unknown bibliographic relation: {overlap.get('bibliographic_relation')}")
        pair = indexes.get("pairs", {}).get(str(overlap.get("query_pair_id")))
        if overlap.get("bibliographic_relation") == "exact_expression_pair_reported":
            if not pair or not pair.get("forrt_summary_record_ids"):
                problems.append(f"exact relation lacks a frozen FORRT pair record: {overlap.get('query_pair_id')}")
            expression_index = indexes.get("expressions", {})
            if pair and any(
                expression_index.get(str(pair.get(field)), {}).get("identity_kind") != "doi"
                for field in ("original_expression_id", "later_expression_id")
            ):
                problems.append(f"exact relation is not a DOI expression pair: {overlap.get('query_pair_id')}")
        for axis in ("effect_relation", "study_relation", "sample_relation", "outcome_relation"):
            if overlap.get(axis) != "not_compared":
                problems.append(f"paper identity improperly resolves {axis}: {overlap.get('query_pair_id')}")

    counts = document.get("counts") or {}
    if len(overlaps) != counts.get("retested_normalized_pairs"):
        problems.append("overlap partition does not cover every Retested normalized pair")
    relation_total = sum((counts.get("bibliographic_relations") or {}).values())
    if relation_total != len(overlaps):
        problems.append("bibliographic relation counts do not conserve the overlap partition")
    addition_relation_total = sum((counts.get("retested_addition_bibliographic_relations") or {}).values())
    if addition_relation_total != counts.get("retested_additions"):
        problems.append("Retested-addition bibliographic relation counts do not conserve Retested additions")
    observed_addition_relations = Counter(
        overlap["bibliographic_relation"]
        for overlap in overlaps
        if overlap.get("built_stratum") == "retested_addition"
    )
    if dict(sorted(observed_addition_relations.items())) != counts.get("retested_addition_bibliographic_relations"):
        problems.append("Retested-addition bibliographic relation counts disagree with overlap decisions")
    if counts.get("retested_built_overlays", 0) + counts.get("retested_additions", 0) != len(overlaps):
        problems.append("overlay/addition counts do not conserve the overlap partition")
    if counts.get("effect_relations_resolved") != 0 or counts.get("certified_new_to_forrt") != 0:
        problems.append("interim v1 overclaims resolved effects or novelty")
    if document.get("coverage", {}).get("assurance_complete") is not False:
        problems.append("interim v1 improperly claims complete assurance")
    if '"/tmp/' in json.dumps(document, ensure_ascii=False, sort_keys=True):
        problems.append("registry contains an ephemeral /tmp evidence locator")
    return problems


def build_from_paths(
    summaries_path: Path = PAIR_SUMMARIES,
    promoted_path: Path = PROMOTED,
    attempts_path: Path = ATTEMPTS,
    reconciled_path: Path = RECONCILED,
    semantic_review_path: Path = SEMANTIC_REVIEW,
    effect_ledger_path: Path = EFFECT_LEDGER,
    policy_path: Path = POLICY,
    raw_manifest_path: Path = RAW_MANIFEST,
) -> tuple[dict[str, Any], list[str]]:
    paths = (
        summaries_path, promoted_path, attempts_path, reconciled_path,
        semantic_review_path, effect_ledger_path, policy_path, raw_manifest_path,
    )
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing reconciliation input(s): " + ", ".join(missing))
    policy = _json(policy_path)
    summaries = _json(summaries_path)
    promoted = _json(promoted_path)
    attempts = _json(attempts_path)
    reconciled = _json(reconciled_path)
    semantic_review = _json(semantic_review_path)
    raw_manifest = _json(raw_manifest_path)
    inputs = [_input_descriptor(path) for path in paths]
    document = build_registry(
        summaries,
        promoted,
        attempts,
        reconciled,
        _effect_ids(effect_ledger_path),
        policy,
        inputs=inputs,
    )
    problems = [
        *_manifest_problems(raw_manifest, policy),
        *_semantic_review_problems(reconciled, semantic_review, semantic_review_path),
        *validate_registry(document, policy),
    ]
    document["validation"] = {
        "structurally_valid": not problems,
        "problems": problems,
        "assurance_complete": bool(document["coverage"]["assurance_complete"]),
    }
    return document, problems


def _write_json(payload: Mapping[str, Any], path: Path, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if compact else json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    ) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
        os.chmod(temporary, 0o644)
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def registry_summary(document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": document["schema_version"],
        "scope": document["scope"],
        "counts": document["counts"],
        "coverage": document["coverage"],
        "validation": document["validation"],
        "input_hashes": {item["path"]: item["sha256"] for item in document["inputs"]},
    }


def generate_and_write(
    summaries_path: Path = PAIR_SUMMARIES,
    promoted_path: Path = PROMOTED,
    attempts_path: Path = ATTEMPTS,
    reconciled_path: Path = RECONCILED,
    semantic_review_path: Path = SEMANTIC_REVIEW,
    effect_ledger_path: Path = EFFECT_LEDGER,
    policy_path: Path = POLICY,
    raw_manifest_path: Path = RAW_MANIFEST,
    output: Path = OUTPUT,
    summary_output: Path = SUMMARY_OUTPUT,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build, structurally validate, and atomically write the two artifacts.

    Incomplete *assurance* is an expected state of v1 and is carried in the
    written document.  Structural problems are different: neither output is
    written when one is present, so a normal site build can fail closed.
    """

    input_paths = (
        summaries_path, promoted_path, attempts_path, reconciled_path,
        semantic_review_path, effect_ledger_path, policy_path, raw_manifest_path,
    )
    path_problems = _output_path_problems(output, summary_output, input_paths)
    if path_problems:
        return None, path_problems
    document, problems = build_from_paths(
        summaries_path, promoted_path, attempts_path, reconciled_path,
        semantic_review_path, effect_ledger_path, policy_path, raw_manifest_path,
    )
    if problems:
        return document, problems
    _write_json(document, output, compact=True)
    _write_json(registry_summary(document), summary_output)
    return document, []


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summaries", type=Path, default=PAIR_SUMMARIES)
    parser.add_argument("--promoted", type=Path, default=PROMOTED)
    parser.add_argument("--attempts", type=Path, default=ATTEMPTS)
    parser.add_argument("--reconciled", type=Path, default=RECONCILED)
    parser.add_argument("--semantic-review", type=Path, default=SEMANTIC_REVIEW)
    parser.add_argument("--effect-ledger", type=Path, default=EFFECT_LEDGER)
    parser.add_argument("--policy", type=Path, default=POLICY)
    parser.add_argument("--raw-manifest", type=Path, default=RAW_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=SUMMARY_OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate in memory without writing")
    args = parser.parse_args(argv)
    if args.check:
        document, problems = build_from_paths(
            args.summaries, args.promoted, args.attempts, args.reconciled,
            args.semantic_review, args.effect_ledger, args.policy, args.raw_manifest,
        )
    else:
        document, problems = generate_and_write(
            args.summaries, args.promoted, args.attempts, args.reconciled,
            args.semantic_review, args.effect_ledger, args.policy, args.raw_manifest,
            args.output, args.summary_output,
        )
        if document is None:
            print("REFUSED registry write:")
            for problem in problems:
                print(f"  - {problem}")
            return 2
    counts = document["counts"]
    print(
        f"{'CHECKED' if args.check else 'WROTE' if not problems else 'REFUSED'} registry "
        f"pairs={counts['retested_normalized_pairs']} rows={counts['retested_reviewed_source_rows']} "
        f"claims={counts['source_scoped_claims']} tests={counts['report_scoped_claim_tests']} "
        f"structural={'PASS' if not problems else 'FAIL'} assurance=INCOMPLETE"
    )
    for problem in problems[:20]:
        print(f"  - {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
