"""Focused contracts for the manually curated original-study explanation layer."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.explanations import (
    ExplanationValidationError,
    attach,
    load,
    validate_holds,
    validate_document,
)


DOI_O = "10.1234/original"
DOI_R = "10.5678/later"
SOURCE_URL = "https://example.org/original"


def promoted_row() -> dict:
    return {
        "doi_o": DOI_O,
        "doi_r": DOI_R,
        "original_source_url": SOURCE_URL,
        # This deliberately tempting value must never enter the explanation
        # payload.  It stands in for every later verdict field on a promoted row.
        "outcome": "failed",
    }


def document(**changes) -> dict:
    record = {
        "original": {
            "claim": "People who received a warm object judged an unfamiliar target as friendlier.",
            "method": "Adults held either a warm or cold object before rating an unfamiliar target.",
            "population": "Adult volunteers recruited for the original laboratory study.",
            "outcome_measure": "Ratings of the unfamiliar target's friendliness.",
        },
        "source": {
            "url": SOURCE_URL,
            "evidence": [
                {
                    "location": "Abstract",
                    "quote": "Participants who held a warm object rated the target as friendlier.",
                    "supports": ["claim", "outcome_measure"],
                },
                {
                    "location": "Methods",
                    "quote": "Adult volunteers held a warm or cold object before rating an unfamiliar target.",
                    "supports": ["method", "population"],
                },
            ],
        },
        "review": {
            "state": "source_reviewed",
            "reviewed_by": "manual-curator",
            "reviewed_on": "2026-09-26",
        },
        "provenance": {
            "kind": "manual_source_review",
            "promoted_pair_doi_r": DOI_R,
        },
    }
    record.update(changes)
    return {"schema_version": 1, "findings": {DOI_O: record}}


class FindingExplanationTests(unittest.TestCase):
    def test_source_reviewed_original_context_is_canonical_and_outcome_free(self) -> None:
        # Input ordering is a curator convenience.  The returned DOI mapping is
        # sorted so it cannot perturb otherwise deterministic build output.
        second = copy.deepcopy(document())
        second["findings"]["10.4321/another"] = copy.deepcopy(second["findings"].pop(DOI_O))
        second["findings"]["10.4321/another"]["provenance"]["promoted_pair_doi_r"] = "10.9876/another-later"
        promoted = [promoted_row(), {
            "doi_o": "10.4321/another", "doi_r": "10.9876/another-later", "original_source_url": SOURCE_URL,
        }]
        # The first row's source is exact and each record gets a fresh copy.
        validated = validate_document(document(), [promoted[0]])
        self.assertEqual(list(validated), [DOI_O])
        findings = {DOI_O: {"doi_o": DOI_O}}
        attach(findings, validated)
        explanation = findings[DOI_O]["explanation"]
        self.assertEqual(explanation["original"]["outcome_measure"], "Ratings of the unfamiliar target's friendliness.")
        self.assertEqual(explanation["review"]["state"], "source_reviewed")
        self.assertEqual(explanation["provenance"]["promoted_pair_doi_r"], DOI_R)
        self.assertNotIn("failed", json.dumps(explanation))

        # The map is canonical regardless of JSON key order.
        first_two = validate_document(second, promoted)
        reordered = {"schema_version": 1, "findings": dict(reversed(list(second["findings"].items())))}
        second_two = validate_document(reordered, promoted)
        self.assertEqual(first_two, second_two)

    def test_later_result_language_and_unreviewed_source_anchors_are_rejected(self) -> None:
        leaked = document()
        leaked["findings"][DOI_O]["original"]["method"] = "Adults repeated the task in a later replication study."
        with self.assertRaisesRegex(ExplanationValidationError, "later outcome"):
            validate_document(leaked, [promoted_row()])

        unanchored = document()
        unanchored["findings"][DOI_O]["provenance"]["promoted_pair_doi_r"] = "10.9999/unreviewed"
        with self.assertRaisesRegex(ExplanationValidationError, "not a reviewed promoted pair"):
            validate_document(unanchored, [promoted_row()])

    def test_research_aim_cannot_stand_in_for_the_observed_claim(self) -> None:
        aim_only = document()
        aim_only["findings"][DOI_O]["original"]["claim"] = (
            "The study examined whether holding a warm object changes judgments of an unfamiliar target."
        )
        with self.assertRaisesRegex(ExplanationValidationError, "observed original result"):
            validate_document(aim_only, [promoted_row()])

    def test_source_evidence_must_cover_every_display_field_and_standalone_review_is_allowed(self) -> None:
        unsupported = document()
        unsupported["findings"][DOI_O]["source"]["evidence"][1]["supports"] = ["method"]
        with self.assertRaisesRegex(ExplanationValidationError, "does not support population"):
            validate_document(unsupported, [promoted_row()])

        standalone = document()
        standalone["findings"][DOI_O]["provenance"]["promoted_pair_doi_r"] = None
        validated = validate_document(standalone, [])
        self.assertEqual(validated[DOI_O]["provenance"]["promoted_pair_doi_r"], None)

    def test_loads_committed_schema_and_refuses_orphaned_originals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "finding_explanations.json"
            path.write_text(json.dumps(document()), encoding="utf-8")
            explanations = load(path, [promoted_row()])
        with self.assertRaisesRegex(ExplanationValidationError, "no built finding exists"):
            attach({}, explanations)

    def test_hold_queue_is_sorted_unique_and_disjoint_from_accepted_records(self) -> None:
        holds = {
            "schema_version": 1,
            "reviewed_on": "2026-09-26",
            "scope": "Current source-review holds, not adverse scientific judgments.",
            "holds": [{
                "doi_o": "10.4321/held",
                "state": "held_source_unavailable",
                "reason": "The directly inspectable original full text was not available in this review lane.",
                "source_url": None,
                "source_batches": ["session_source_batch_1"],
            }],
        }
        self.assertEqual(validate_holds(holds, {}), holds["holds"])

        overlap = copy.deepcopy(holds)
        overlap["holds"][0]["doi_o"] = DOI_O
        with self.assertRaisesRegex(ExplanationValidationError, "already an accepted explanation"):
            validate_holds(overlap, {DOI_O: document()["findings"][DOI_O]})

        duplicate = copy.deepcopy(holds)
        duplicate["holds"].append(copy.deepcopy(duplicate["holds"][0]))
        with self.assertRaisesRegex(ExplanationValidationError, "duplicate held DOI"):
            validate_holds(duplicate, {})


if __name__ == "__main__":
    unittest.main()
