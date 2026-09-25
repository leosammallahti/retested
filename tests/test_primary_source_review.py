"""Regression checks for source-specific replication review gates."""
from __future__ import annotations

import unittest

from pipeline.primary_source_review import (
    _gate, _identity_quote, _section_bounds, _target_reasons,
)


class PrimarySourceReviewTests(unittest.TestCase):
    def test_exact_doi_plus_retest_quote_both_required(self):
        row = {
            "original_doi": "10.1234/original",
            "original_title": "A distinct mood effect",
            "original_year": 2020,
            "original_abstract_cached": "Higher scores were associated with lower relief ratings in the original test.",
        }
        texts = {
            "original_abstract": row["original_abstract_cached"],
            "later_abstract": "We repeated Smith et al. (2020) and found lower relief ratings.",
            "later_link_text": "We repeated Smith et al. (2020) to test the distinct mood effect.",
            "later_methods_text": "A new sample of participants was recruited for this experiment.",
            "later_results_text": "Higher scores were again associated with lower relief ratings.",
            "full_text_contains_original_doi": False,
            "original_reference_number": "",
        }
        answer = {
            "original_link": {
                "status": "supported",
                "quote": "We repeated Smith et al. (2020) to test the distinct mood effect.",
                "source": "later_link_text",
            },
            "new_participants": {
                "status": "supported",
                "later_quote": "A new sample of participants was recruited for this experiment.",
                "later_source": "later_methods_text",
                "basis": "explicit_new",
            },
            "exact_result": {
                "status": "supported",
                "effect_claim": "Higher scores were associated with lower relief ratings.",
                "original_quote": "Higher scores were associated with lower relief ratings in the original test.",
                "later_target_quote": "We repeated Smith et al. (2020) to test the distinct mood effect.",
                "later_target_source": "later_link_text",
                "later_result_quote": "Higher scores were again associated with lower relief ratings.",
                "later_result_source": "later_results_text",
                "outcome": "successful",
            },
            "confidence": .92,
        }
        evidence = {"references": [{"doi": row["original_doi"], "author": "Smith", "year": "2020"}]}
        self.assertEqual(_gate(row, evidence, texts, answer), [])
        missing = _gate(row, {"references": []}, texts, answer)
        self.assertTrue(any("exact DOI absent" in reason for reason in missing))
        generic = dict(answer["original_link"], quote="We repeated this previous study on the mood effect.")
        answer["original_link"] = generic
        evidence = {"references": [{"doi": row["original_doi"], "author": "Smith", "year": "2020"}]}
        self.assertFalse(_identity_quote(row, evidence, texts, generic["quote"]))

    def test_required_effect_cannot_drift_to_other_subgroup(self):
        row = {
            "target_effect_name": "Four patterns of negative emotional eating",
            "target_effect_claim": "Negative emotional eating profiles include no eating, overeating, undereating, and combined eating.",
        }
        wrong = {
            "effect_claim": "The combined group has the highest psychological distress.",
            "original_quote": "The combined group had the highest distress.",
            "later_result_quote": "All groups showed greater distress than controls.",
        }
        reasons = _target_reasons(row, wrong)
        self.assertTrue(any("drifted" in reason for reason in reasons))
        self.assertTrue(any("numeric scope" in reason for reason in reasons))

    def test_result_prose_is_not_a_results_section(self):
        mirror = "a" * 2000 + " Results showed a pattern in the introduction. " + "b" * 3000
        self.assertEqual(_section_bounds(mirror)[1], len(mirror))
        article = "a" * 2000 + " Methods Participants were recruited. " + "b" * 500
        article += " Results Descriptive statistics were reported. " + "c" * 500
        article += " Discussion This interprets the findings."
        methods, results, discussion = _section_bounds(article)
        self.assertLess(methods, results)
        self.assertLess(results, discussion)


if __name__ == "__main__":
    unittest.main()
