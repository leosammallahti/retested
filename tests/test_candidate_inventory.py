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


if __name__ == "__main__":
    unittest.main()

