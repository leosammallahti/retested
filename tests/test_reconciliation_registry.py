"""Focused grain and identity-boundary tests for reconciliation_registry."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.ids import norm_name
from pipeline.reconciliation_registry import (
    _semantic_review_problems,
    _output_path_problems,
    _title_key,
    build_registry,
    main as registry_main,
    validate_registry,
)


ORIGINAL = "10.1000/original"
LATER = "10.1000/later"
PROMOTED_PATH = "data/curated/promoted_pairs.json"
FORRT_PATH = "data/raw/forrt/fixture.csv"


def _provenance(identifier: str, source: str, path: str, row: int) -> dict:
    return {"id": identifier, "source": source, "path": path, "row": row}


def _summary_record(
    *, record_id: str, source: str, path: str, row: int, alias: bool = False,
    original: str = ORIGINAL, later: str = LATER,
) -> dict:
    original_identifiers = [{"kind": "doi", "value": original}]
    if alias:
        # This is a source assertion about two citable expressions.  It must
        # remain an assertion/edge, not collapse either expression identity.
        original_identifiers.append({"kind": "doi", "value": "10.1000/original-version"})
    return {
        "record_id": record_id,
        "record_kind": "pair",
        "original_key": f"doi:{original}",
        "replication_key": f"doi:{later}",
        "doi_o": original,
        "doi_r": later,
        "identifiers": {
            "original": original_identifiers,
            "replication": [{"kind": "doi", "value": later}],
        },
        "components": {
            "original_title": [{"text": "Original expression"}],
            "replication_title": [{"text": "Later expression"}],
        },
        "observed_result": "A source-scoped result statement.",
        "outcome_labels": [{"label": "successful", "provenance_ids": [f"pv-{record_id}"]}],
        "provenance": [_provenance(f"pv-{record_id}", source, path, row)],
    }


def _promoted(effect_name: str) -> dict:
    return {
        "doi_o": ORIGINAL,
        "doi_r": LATER,
        "effect_name": effect_name,
        "effect_claim": f"{effect_name} is observed in the original report.",
        "effect_claim_quote": f"The original report observed {effect_name}.",
        "original_source_url": "https://example.test/original",
        "replication_target_quote": f"The later report tested {effect_name}.",
        "replication_source_url": "https://example.test/later",
        "outcome": "successful",
        "outcome_quote": f"The later report observed {effect_name}.",
        "outcome_quote_source": "results",
        "reviewed_by": "test reviewer",
        "reviewed_on": "2026-09-26",
    }


def _policy() -> dict:
    return {
        "scope": "synthetic frozen comparison",
        "source_layers": {
            "source_reviewed": "retested_reviewed",
            "published": "forrt_public",
        },
        "membership_priority": ["published"],
        "bibliographic_relations": ["exact_expression_pair_reported"],
        "pinned_current_sources": [],
    }


def _document(
    *,
    extra_corpus_records: tuple[dict, ...] = (),
    attempt_sources: tuple[str, ...] = ("retested", "flora"),
    reconciled_records: tuple[dict, ...] = (),
) -> tuple[dict, dict]:
    """A one-paper-pair fixture carrying two independently scoped effects."""
    effect_a, effect_b = "Effect alpha", "Effect beta"
    query_record = _summary_record(
        record_id="rq-1", source="retested_promoted", path=PROMOTED_PATH, row=1,
    )
    query_record["provenance"].append(
        _provenance("pv-rq-2", "retested_promoted", PROMOTED_PATH, 2)
    )
    summaries = {
        "sources": [
            {
                "source": "retested_promoted", "status": "source_reviewed",
                "path": PROMOTED_PATH, "sha256": "a" * 64,
                "rows_read": 2, "rows_indexed": 2, "pair_references": 2,
                "later_status_references": 0,
            },
            {
                "source": "forrt_fixture", "status": "published",
                "path": FORRT_PATH, "sha256": "b" * 64,
                "rows_read": 1, "rows_indexed": 1, "pair_references": 1,
                "later_status_references": 0,
            },
        ],
        "query_records": [query_record],
        "corpus_records": [
            _summary_record(
                record_id="fq-1", source="forrt_fixture", path=FORRT_PATH, row=7, alias=True,
            ),
            _summary_record(
                record_id="fq-self", source="forrt_fixture", path=FORRT_PATH, row=8,
                original="10.1000/within-paper", later="10.1000/within-paper",
            ),
            *extra_corpus_records,
        ],
    }
    promoted = [_promoted(effect_a), _promoted(effect_b)]
    attempts = {
        "attempt-1": {
            "id": "attempt-1", "doi_o": ORIGINAL, "doi_r": LATER,
            "sources": list(attempt_sources),
        },
    }
    effect_ids = {norm_name(effect_a): "ef-alpha", norm_name(effect_b): "ef-beta"}
    policy = _policy()
    return build_registry(
        summaries, promoted, attempts, {"records": list(reconciled_records)}, effect_ids, policy,
    ), policy


class ReconciliationRegistryTests(unittest.TestCase):
    def test_two_effects_on_one_doi_pair_remain_two_claim_tests(self):
        document, policy = _document()

        self.assertEqual(document["counts"]["retested_normalized_pairs"], 1)
        self.assertEqual(document["counts"]["source_scoped_claims"], 2)
        self.assertEqual(document["counts"]["report_scoped_claim_tests"], 2)
        self.assertEqual(
            {test["claim_id"] for test in document["claim_tests"]},
            {claim["id"] for claim in document["claims"]},
        )
        self.assertEqual(validate_registry(document, policy), [])

    def test_retested_addition_relation_counts_are_partitioned_and_validated(self):
        document, policy = _document(
            attempt_sources=("retested",),
            reconciled_records=({
                "doi_o": ORIGINAL,
                "doi_r": LATER,
                "reconciled_classification": "same_pair_recorded",
            },),
        )

        self.assertEqual(document["counts"]["retested_additions"], 1)
        self.assertEqual(
            document["counts"]["retested_addition_bibliographic_relations"],
            {"exact_expression_pair_reported": 1},
        )
        self.assertEqual(validate_registry(document, policy), [])

        changed = copy.deepcopy(document)
        changed["counts"]["retested_addition_bibliographic_relations"] = {}
        self.assertTrue(any(
            "Retested-addition bibliographic relation counts do not conserve" in problem
            for problem in validate_registry(changed, policy)
        ))

    def test_exact_paper_pair_never_resolves_effect_study_or_sample_axes(self):
        document, _ = _document()

        self.assertEqual(
            document["overlap_decisions"][0]["bibliographic_relation"],
            "exact_expression_pair_reported",
        )
        for overlap in document["overlap_decisions"]:
            self.assertEqual(overlap["effect_relation"], "not_compared")
            self.assertEqual(overlap["study_relation"], "not_compared")
            self.assertEqual(overlap["sample_relation"], "not_compared")
            self.assertEqual(overlap["outcome_relation"], "not_compared")
        self.assertTrue(all(claim["study_id"] is None for claim in document["claims"]))
        self.assertTrue(all(test["replication_study_id"] is None and not test["sample_ids"]
                            for test in document["claim_tests"]))
        self.assertEqual(document["studies"], [])
        self.assertEqual(document["samples"], [])

    def test_source_reported_expression_alias_is_explicit_and_structurally_valid(self):
        document, policy = _document()

        aliases = [
            assertion for assertion in document["work_identity_assertions"]
            if assertion["predicate"] == "source_asserted_identifier_alias"
        ]
        self.assertEqual(len(aliases), 1)
        self.assertEqual(aliases[0]["review_status"], "source_reported_not_curator_merged")
        self.assertEqual(aliases[0]["side"], "original")
        self.assertEqual(len(aliases[0]["expression_ids"]), 2)
        self.assertTrue(all(
            expression["work_identity_status"] == "not_materialized"
            for expression in document["expressions"]
        ))
        self.assertEqual(validate_registry(document, policy), [])

    def test_same_expression_pair_is_flagged_as_identity_anomaly(self):
        document, policy = _document()

        same_expression = [
            pair for pair in document["pairs"]
            if pair["original_expression_id"] == pair["later_expression_id"]
        ]
        self.assertEqual(len(same_expression), 1)
        self.assertEqual(
            same_expression[0]["expression_pair_scope"],
            "source_reported_same_expression_anomaly",
        )
        self.assertTrue(same_expression[0]["requires_identity_review"])
        self.assertEqual(document["counts"]["source_reported_same_expression_anomalies"], 1)
        self.assertEqual(validate_registry(document, policy), [])

    def test_title_only_primary_keys_are_record_scoped_candidates_not_exact_identity(self):
        title_records = []
        for record_id, row in (("title-1", 20), ("title-2", 21)):
            record = _summary_record(
                record_id=record_id, source="forrt_fixture", path=FORRT_PATH, row=row,
            )
            record["original_key"] = _title_key("Shared original title")
            record["replication_key"] = _title_key("Shared later title")
            record["identifiers"] = {
                "original": [{"kind": "title", "value": "Shared original title"}],
                "replication": [{"kind": "title", "value": "Shared later title"}],
            }
            title_records.append(record)

        document, policy = _document(extra_corpus_records=tuple(title_records))
        title_expressions = [
            expression for expression in document["expressions"]
            if expression["identity_kind"] == "title-candidate"
        ]
        self.assertEqual(len(title_expressions), 4)
        self.assertEqual(len({expression["identity_key"] for expression in title_expressions}), 4)
        self.assertTrue(all(
            expression["identity_status"] == "record_scoped_title_candidate_not_identity"
            for expression in title_expressions
        ))
        self.assertFalse(any(
            expression["identity_key"].startswith("title-sha256:")
            for expression in document["expressions"]
        ))
        self.assertEqual(document["overlap_decisions"][0]["bibliographic_relation"],
                         "exact_expression_pair_reported")
        self.assertEqual(validate_registry(document, policy), [])

    def test_source_summary_records_are_self_contained_and_observations_reference_them(self):
        document, policy = _document()
        records = {record["id"]: record for record in document["source_summary_records"]}

        self.assertEqual(len(records), document["counts"]["forrt_summary_records"] + 1)
        for record in records.values():
            self.assertTrue(record["payload_sha256"])
            self.assertIn(record["origin"], {"retested", "forrt"})
            self.assertIn("upstream_summary_record_id", record)
            self.assertIn("identifiers", record)
            self.assertIn("components", record)
            self.assertIn("outcome_labels", record)
            self.assertIn("observed_result", record)
            self.assertIn("later_expression_id", record)
        for observation in document["source_observations"]:
            self.assertIn(observation["summary_record_id"], records)
            summary_record = records[observation["summary_record_id"]]
            self.assertEqual(observation["later_expression_id"], summary_record["later_expression_id"])
            self.assertEqual(observation["pair_id"], summary_record["pair_id"])
        self.assertEqual(validate_registry(document, policy), [])

    def test_stable_evidence_location_mapping_removes_tmp_locators(self):
        reconciled = ({
            "doi_o": ORIGINAL,
            "doi_r": LATER,
            "reconciled_classification": "same_pair_recorded",
            "semantic_adjudication": {
                "decision": "confirmed_same_pair",
                "query_record_id": "rq-1",
                "candidate_record_ids": ["fq-1"],
                "original_work_matches": True,
                "later_work_matches": True,
                "evidence": "Frozen source and reviewed queue identify both expressions.",
                "evidence_locations": [
                    {"path": "/tmp/retested_live_forrt_extractor.csv", "row": 7},
                    {"path": "/tmp/retested_embedding_review_all.json", "row": 2},
                ],
            },
        },)
        document, policy = _document(
            attempt_sources=("retested",), reconciled_records=reconciled,
        )

        reference = document["overlap_decisions"][0]["reconciliation_reference"]
        locations = reference["semantic_adjudication"]["evidence_locations"]
        self.assertEqual(locations[0]["path"],
                         "data/raw/forrt/snapshots/2026-09-26/flora-extractor_extracted.csv")
        self.assertEqual(locations[1]["path"], "data/curated/forrt_semantic_match_review_20260926.json")
        self.assertEqual(locations[1]["record_selector"], {"query_record_id": "rq-1"})
        self.assertNotIn('"/tmp/', json.dumps(document, sort_keys=True))
        self.assertEqual(validate_registry(document, policy), [])

    def test_exact_expression_relation_requires_a_frozen_forrt_pair_record(self):
        document, policy = _document()
        pair_id = document["overlap_decisions"][0]["query_pair_id"]
        changed = copy.deepcopy(document)
        pair = next(pair for pair in changed["pairs"] if pair["id"] == pair_id)
        pair["forrt_summary_record_ids"] = []

        self.assertTrue(any(
            "exact relation lacks a frozen FORRT pair record" in problem
            for problem in validate_registry(changed, policy)
        ))

    def test_semantic_review_artifact_is_cross_checked_against_reconciliation(self):
        decision = {
            "query_record_id": "rq-1",
            "doi_o": ORIGINAL,
            "doi_r": LATER,
            "decision": "related_but_distinct",
            "candidate_record_ids": ["fq-1"],
            "original_work_matches": True,
            "later_work_matches": False,
            "evidence": "The later works differ.",
            "evidence_locations": [{"url": "https://example.test/evidence"}],
            "top_cosine_similarity": 0.9,
        }
        semantic_review = {
            "decisions": [decision],
            "summary": {"counts": {"related_but_distinct": 1}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "semantic.json"
            path.write_text(json.dumps(semantic_review), encoding="utf-8")
            reconciled = {
                "inputs": {
                    "semantic_adjudication": {
                        "path": str(path),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    },
                },
                "records": [{
                    "doi_o": ORIGINAL,
                    "doi_r": LATER,
                    "semantic_adjudication": {
                        key: decision[key] for key in (
                            "query_record_id", "decision", "candidate_record_ids",
                            "original_work_matches", "later_work_matches", "evidence",
                            "evidence_locations", "top_cosine_similarity",
                        )
                    },
                }],
            }
            self.assertEqual(
                _semantic_review_problems(reconciled, semantic_review, path), [],
            )
            changed = copy.deepcopy(reconciled)
            changed["records"][0]["semantic_adjudication"]["evidence"] = "changed"
            self.assertTrue(any(
                "differs from review artifact" in problem
                for problem in _semantic_review_problems(changed, semantic_review, path)
            ))

    def test_output_paths_cannot_collide_with_each_other_or_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            output_path = root / "registry.json"
            summary_path = root / "summary.json"
            self.assertEqual(
                _output_path_problems(output_path, summary_path, [input_path]), [],
            )
            self.assertTrue(any(
                "same path" in problem
                for problem in _output_path_problems(output_path, output_path, [input_path])
            ))
            self.assertTrue(any(
                "overwrite an input" in problem
                for problem in _output_path_problems(input_path, summary_path, [input_path])
            ))
            self.assertTrue(any(
                "overwrite an input" in problem
                for problem in _output_path_problems(output_path, input_path, [input_path])
            ))

    def test_write_mode_never_writes_a_structurally_invalid_registry(self):
        invalid_document = {
            "schema_version": "reconciliation-registry/v1",
            "scope": "test",
            "inputs": [],
            "counts": {
                "retested_normalized_pairs": 1,
                "retested_reviewed_source_rows": 1,
                "source_scoped_claims": 1,
                "report_scoped_claim_tests": 1,
            },
            "coverage": {"assurance_complete": False},
            "validation": {
                "structurally_valid": False,
                "problems": ["synthetic problem"],
                "assurance_complete": False,
            },
        }
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "pipeline.reconciliation_registry.build_from_paths",
            return_value=(invalid_document, ["synthetic problem"]),
        ), mock.patch("pipeline.reconciliation_registry._write_json") as write:
            result = registry_main([
                "--output", str(Path(directory) / "registry.json"),
                "--summary-output", str(Path(directory) / "summary.json"),
            ])
        self.assertEqual(result, 1)
        write.assert_not_called()

    def test_validation_rejects_fabricated_study_sample_and_result_identities(self):
        document, policy = _document()
        mutations = (
            ("study", lambda data: data["claims"][0].update(study_id="st-invented"),
             "v1 claim fabricates study identity"),
            ("replication study", lambda data: data["claim_tests"][0].update(replication_study_id="st-invented"),
             "v1 claim test fabricates study/sample identity"),
            ("sample", lambda data: data["claim_tests"][0].update(sample_ids=["sa-invented"]),
             "v1 claim test fabricates study/sample identity"),
            ("result", lambda data: data["result_assessments"][0].update(result_id="re-invented"),
             "v1 assessment fabricates contrast result identity"),
        )

        for name, mutate, expected in mutations:
            with self.subTest(identity=name):
                changed = copy.deepcopy(document)
                mutate(changed)
                self.assertTrue(any(expected in problem for problem in validate_registry(changed, policy)))

    def test_build_is_deterministic_for_identical_inputs(self):
        first, _ = _document()
        second, _ = _document()

        self.assertEqual(first, second)
        generated_tables = (
            "source_snapshots", "expressions", "work_identity_assertions", "source_summary_records",
            "pairs", "source_observations", "claims", "claim_tests", "result_assessments",
        )
        identifier = re.compile(r"^(?:sn|ex|wa|sr|pr|ob|cl|ct|ra)_[0-9a-f]{64}$")
        for table in generated_tables:
            with self.subTest(table=table):
                self.assertTrue(all(identifier.fullmatch(row["id"]) for row in first[table]))
                self.assertEqual([row["id"] for row in first[table]], [row["id"] for row in second[table]])


if __name__ == "__main__":
    unittest.main()
