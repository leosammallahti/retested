"""The explanation-coverage denominator is transparent and priority-disjoint."""
from __future__ import annotations

import unittest

from pipeline.stats import finding_context_coverage


class FindingContextCoverageTests(unittest.TestCase):
    def test_tiers_follow_pre_guess_fallback_order_without_promoting_titles(self) -> None:
        g = {
            "findings": {
                "source": {"attempts": ["a-source"], "explanation": {"review": {"state": "source_reviewed"}}},
                "game-context": {"attempts": ["a-game"], "game_contexts": [{"claim": "Plain", "method": "Method"}]},
                "reviewed-claim": {"attempts": ["a-reviewed"]},
                "forrt-claim": {"attempts": ["a-forrt"]},
                "named-effect": {"attempts": ["a-named"], "effects": ["fx_1"]},
                "title": {"attempts": ["a-title"]},
                "thin": {"attempts": ["a-thin"]},
            },
            "attempts": {
                "a-source": {},
                "a-game": {},
                "a-reviewed": {"retested_review": {"original_claim_quote": "A source reviewed original claim."}},
                "a-forrt": {"rows": [{"claim_text_o": "A FORRT-coded original claim."}]},
                "a-named": {},
                "a-title": {},
                "a-thin": {},
            },
            "papers": {"title": {"title": "A title is not source-reviewed context."}},
        }
        coverage = finding_context_coverage(g)
        self.assertEqual(coverage, {
            "denominator": 7,
            "source_reviewed_explanation": 1,
            "plain_language_game_context": 1,
            "fallback_source_reviewed_claim": 1,
            "fallback_forrt_coded_claim": 1,
            "fallback_named_effect": 1,
            "fallback_title_only": 1,
            "no_context": 1,
        })
        self.assertEqual(sum(value for key, value in coverage.items() if key != "denominator"), coverage["denominator"])

    def test_unreviewed_explanation_does_not_count_as_source_reviewed(self) -> None:
        coverage = finding_context_coverage({
            "findings": {"doi": {"attempts": [], "explanation": {"review": {"state": "draft"}}}},
            "attempts": {}, "papers": {"doi": {"title": "Only a title"}},
        })
        self.assertEqual(coverage["source_reviewed_explanation"], 0)
        self.assertEqual(coverage["fallback_title_only"], 1)


if __name__ == "__main__":
    unittest.main()
