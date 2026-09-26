"""Contracts for the answer-separated, balanced daily game schedule."""

from __future__ import annotations

import unittest

from pipeline.export import _daily_decks


class DailyGameExportTests(unittest.TestCase):
    def test_daily_schedules_are_balanced_deterministic_and_id_only(self) -> None:
        items: list[dict] = []
        reveals: dict[str, dict] = {}
        for tier, count in (("study", 8), ("famous", 3)):
            for answer in ("successful", "failed"):
                for index in range(count):
                    card_id = f"{tier}-{answer}-{index}"
                    items.append({"id": card_id, "tier": tier, "written": True, "claim": "A claim."})
                    reveals[card_id] = {"id": card_id, "answer": answer}

        first = _daily_decks(items, reveals)
        second = _daily_decks(items, reveals)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 366)
        by_id = {item["id"]: item for item in items}
        for card_ids in first.values():
            self.assertEqual(len(card_ids), 10)
            self.assertTrue(all(isinstance(card_id, str) for card_id in card_ids))
            self.assertEqual(sum(by_id[card_id]["tier"] == "study" for card_id in card_ids), 8)
            self.assertEqual(sum(by_id[card_id]["tier"] == "famous" for card_id in card_ids), 2)
            self.assertEqual(sum(reveals[card_id]["answer"] == "successful" for card_id in card_ids), 5)
            self.assertEqual(sum(reveals[card_id]["answer"] == "failed" for card_id in card_ids), 5)

        self.assertTrue(all("answer" not in item and "daily_bucket" not in item for item in items))


if __name__ == "__main__":
    unittest.main()
