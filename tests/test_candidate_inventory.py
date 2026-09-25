"""Full-registry candidate check, including DOI aliases and multi-original papers."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import candidate_inventory


class CandidateInventoryTests(unittest.TestCase):
    def test_exact_pair_is_known_but_different_original_remains_new(self):
        attempts = {
            "known": {
                "doi_o": "10.1037//0022-3514.79.1.49",
                "doi_r": "10.1177/0956797619831612",
                "sources": ["fred", "legacy"],
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "attempts.json"
            path.write_text(json.dumps(attempts))
            with (
                patch.object(candidate_inventory, "ATTEMPTS", path),
                patch.object(candidate_inventory, "PROMOTED", Path(folder) / "missing.json"),
                patch.object(
                    candidate_inventory,
                    "load_known_replication_dois",
                    return_value={"10.1177/0956797619831612"},
                ),
            ):
                result = candidate_inventory.inventory(
                    ["10.1177/0956797619831612"],
                    [
                        {"doi_o": "10.1037/0022-3514.79.1.49", "doi_r": "10.1177/0956797619831612"},
                        {"doi_o": "10.1037/another", "doi_r": "10.1177/0956797619831612"},
                    ],
                )

        self.assertEqual(result["papers"][0]["site_pair_count"], 1)
        self.assertTrue(result["papers"][0]["forrt_raw_knows_later_paper"])
        self.assertTrue(result["pairs"][0]["already_on_site"])
        self.assertFalse(result["pairs"][1]["already_on_site"])


    def test_same_title_different_doi_flags_existing_version(self):
        attempts = {
            "preprint": {
                "doi_o": "10.1037/original",
                "doi_r": "10.31234/osf.io/vkarq",
                "title_r": "Revisiting the Effect of Team Passion: A Replication",
                "sources": ["retested"],
            }
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "attempts.json"
            path.write_text(json.dumps(attempts))
            with (
                patch.object(candidate_inventory, "ATTEMPTS", path),
                patch.object(candidate_inventory, "PROMOTED", Path(folder) / "missing.json"),
                patch.object(candidate_inventory, "load_known_replication_dois", return_value=set()),
            ):
                result = candidate_inventory.inventory([], [{
                    "doi_o": "10.1037/original",
                    "doi_r": "10.1177/published",
                    "replication_title": "Revisiting the effect of team passion: a replication",
                }])
        pair = result["pairs"][0]
        self.assertFalse(pair["already_on_site"])
        self.assertTrue(pair["same_work_same_original_on_site"])
        self.assertEqual(pair["same_title_site_versions"], ["10.31234/osf.io/vkarq"])


if __name__ == "__main__":
    unittest.main()

