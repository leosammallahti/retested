"""Focused checks for reviewed pairs entering the counted registry."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.ids import EffectLedger
from pipeline.promoted import load, validate
from pipeline.registry import build


def reviewed_pair() -> dict:
    return {
        "candidate_id": "10.1177/2158244014553587",
        "doi_o": "10.1037//0022-3514.44.4.817",
        "doi_r": "10.1177/2158244014553587",
        "effect_name": "Aggressive cartoons are funnier",
        "effect_claim": "Cartoons with aggressive content were rated as funnier than other cartoons.",
        "effect_claim_quote": "The aggressive cartoons were rated as funnier.",
        "original_source_url": "https://pubmed.ncbi.nlm.nih.gov/6842367/",
        "original_title": "Aggressive cartoons are funnier",
        "original_year": 1983,
        "original_authors": "Example Author",
        "replication_title": "The humour of aggressive cartoons: A replication",
        "replication_year": 2014,
        "replication_authors": "Example Replicator",
        "replication_source_url": "https://doi.org/10.1177/2158244014553587",
        "replication_target_quote": "This study replicated the aggressive cartoons finding.",
        "outcome": "failed",
        "outcome_quote": "The original finding was not replicated in this sample.",
        "outcome_quote_source": "abstract",
        "reviewed_by": "Codex source review",
        "reviewed_on": "2026-09-24",
    }


def graph(row: dict, flora: list[dict] | None = None) -> dict:
    src = {
        "flora": flora or [], "fred": [], "legacy": {"data": [], "rr": []},
        "famous": [], "openalex": {}, "merges": [], "promoted": validate([copy.deepcopy(row)]),
    }
    with tempfile.TemporaryDirectory() as folder:
        return build(src, EffectLedger(Path(folder) / "effect_ids.csv"))


class PromotionTests(unittest.TestCase):
    def test_validation_rejects_bad_doi_order_duplicates_and_unsourced_claim(self):
        base = reviewed_pair()
        for field, value in (
            ("doi_o", "https://doi.org/10.1037//0022-3514.44.4.817"),
            ("doi_r", base["doi_o"]),
            ("original_year", 2020),
            ("effect_claim", "It was replicated."),
            ("effect_claim_quote", ""),
        ):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(base)
                changed[field] = value
                with self.assertRaises(ValueError):
                    validate([changed])
        with self.assertRaises(ValueError):
            validate([copy.deepcopy(base), copy.deepcopy(base)])

    def test_explicit_alias_needs_matching_discovery_title_and_year(self):
        row = reviewed_pair()
        row["duplicate_candidate_ids"] = ["W7160481126"]
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / "data"
            curated, discovery = data / "curated", data / "discovery"
            curated.mkdir(parents=True)
            discovery.mkdir(parents=True)
            file = curated / "promoted_pairs.json"
            file.write_text(json.dumps([row]), encoding="utf-8")
            primary = {
                "cid": row["candidate_id"], "doi_r": row["doi_r"],
                "title_r": row["replication_title"], "year_r": row["replication_year"],
                "author_surnames_r": ["smith", "jones"],
            }
            alias = {
                "cid": "W7160481126", "doi_r": None,
                "title_r": row["replication_title"], "year_r": row["replication_year"],
                "author_surnames_r": ["jones", "smith"],
            }
            triaged = discovery / "triaged.json"
            triaged.write_text(json.dumps([primary, alias]), encoding="utf-8")
            self.assertEqual(load(file)[0]["duplicate_candidate_ids"], ["W7160481126"])
            alias["author_surnames_r"] = ["other", "author"]
            triaged.write_text(json.dumps([primary, alias]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load(file)
            alias["author_surnames_r"] = ["jones", "smith"]
            alias["title_r"] = "A different paper"
            triaged.write_text(json.dumps([primary, alias]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load(file)

    def test_new_pair_creates_named_effect_finding_and_attempt(self):
        row = reviewed_pair()
        result = graph(row)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(len(result["effects"]), 1)
        attempt = next(iter(result["attempts"].values()))
        effect = next(iter(result["effects"].values()))
        self.assertEqual(attempt["outcome"], "failed")
        self.assertEqual(attempt["sources"], ["retested"])
        self.assertEqual(effect["name_sources"], ["retested"])
        self.assertEqual(effect["originals"], [row["doi_o"]])
        self.assertEqual(effect["attempts"], [attempt["id"]])
        self.assertEqual(attempt["retested_review"]["candidate_id"], row["candidate_id"])

    def test_doi_fold_keeps_effect_link_and_forrt_verdict_priority(self):
        row = reviewed_pair()
        canonical = row["doi_o"].replace("//", "/")
        flora = [{
            "doi_o": canonical, "doi_r": row["doi_r"],
            "title_o": row["original_title"], "year_o": str(row["original_year"]),
            "title_r": row["replication_title"], "year_r": str(row["replication_year"]),
            "outcome": "successful", "type": "replication",
            "outcome_quote": "The effect held in this sample.",
            "outcome_quote_source": "abstract",
        }]
        result = graph(row, flora)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(list(result["findings"]), [canonical])
        attempt = next(iter(result["attempts"].values()))
        effect = next(iter(result["effects"].values()))
        self.assertEqual(attempt["outcome"], "successful")
        self.assertTrue(attempt["sources_disagree"])
        self.assertEqual(set(attempt["sources"]), {"flora", "retested"})
        self.assertEqual(effect["originals"], [canonical])
        self.assertEqual(effect["attempts"], [attempt["id"]])


if __name__ == "__main__":
    unittest.main()
