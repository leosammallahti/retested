"""Regression tests for duplicate DOI deposits before model review."""
from __future__ import annotations

import unittest

from pipeline.doi_aliases import find_aliases


class DoiAliasTests(unittest.TestCase):
    def test_two_verified_psychological_reports_aliases(self) -> None:
        curated = [
            {
                "doi_o": "10.1027/0227-5910.19.2.62",
                "doi_r": "10.2466/pr0.1999.84.3.726",
                "replication_title": "Prevalence of Malingering in Suicidal Psychiatric Inpatients: A Replication",
                "replication_year": 1999,
            },
            {
                "doi_o": "10.2466/pr0.2000.86.2.611",
                "doi_r": "10.2466/pr0.2002.90.2.515",
                "replication_title": "Leaders' Anticipated and Targets' Self-Reported Resistance to Task Assignments: A Replication",
                "replication_year": 2002,
            },
        ]
        candidates = [
            {"candidate_id": "W4251709755", "doi_o": curated[0]["doi_o"], "doi_r": "10.2466/pr0.84.3.726-730"},
            {"candidate_id": "W4255798523", "doi_o": curated[1]["doi_o"], "doi_r": "10.2466/pr0.90.2.515-520"},
        ]
        sources = [
            {
                "replication_candidate_id": candidate["candidate_id"],
                "replication_doi": candidate["doi_r"],
                "replication_title": curated[index]["replication_title"].upper(),
                "replication_year": curated[index]["replication_year"],
            }
            for index, candidate in enumerate(candidates)
        ]
        results = find_aliases(candidates, sources, curated)
        self.assertEqual([row["status"] for row in results], ["likely_doi_alias", "likely_doi_alias"])
        self.assertEqual(
            [row["curated_doi"] for row in results],
            ["10.2466/pr0.1999.84.3.726", "10.2466/pr0.2002.90.2.515"],
        )

    def test_same_title_different_original_is_not_an_alias(self) -> None:
        curated = [{
            "doi_o": "10.1000/original-a", "doi_r": "10.1000/replica-a",
            "replication_title": "A Replication", "replication_year": 2002,
        }]
        candidate = {"doi_o": "10.1000/original-b", "doi_r": "10.1000/replica-b"}
        source = {"replication_doi": candidate["doi_r"], "replication_title": "A Replication", "replication_year": 2002}
        self.assertEqual(find_aliases([candidate], [source], curated)[0]["status"], "unmatched")


if __name__ == "__main__":
    unittest.main()
