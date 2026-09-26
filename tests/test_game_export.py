"""Contracts for the answer-separated, balanced daily game schedule."""

from __future__ import annotations

import unittest

from pipeline.export import _daily_decks
from pipeline.game import context_ready


class DailyGameExportTests(unittest.TestCase):
    def test_context_contract_requires_written_claim_and_experiment_explanation(self) -> None:
        complete = {
            "written": True,
            "claim": "People make different choices after receiving different information.",
            "method": "60 adults read one of two short descriptions and then made a choice.",
        }
        self.assertTrue(context_ready(complete))
        self.assertFalse(context_ready({**complete, "written": False}))
        self.assertFalse(context_ready({**complete, "method": None}))
        self.assertFalse(context_ready({**complete, "claim": "It replicated."}))

    def test_daily_schedules_are_balanced_deterministic_and_id_only(self) -> None:
        items: list[dict] = []
        reveals: dict[str, dict] = {}
        for tier, count in (("study", 8), ("famous", 3)):
            for answer in ("successful", "failed"):
                for index in range(count):
                    card_id = f"{tier}-{answer}-{index}"
                    items.append({
                        "id": card_id, "tier": tier, "written": True, "context_ready": True,
                        "claim": "People make different choices after receiving different information.",
                        "method": "60 adults read one of two short descriptions and then made a choice.",
                    })
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

    def test_daily_schedule_refuses_cards_without_plain_language_context(self) -> None:
        items, reveals = [], {}
        for answer in ("successful", "failed"):
            for index in range(3 if answer == "successful" else 4):
                card_id = f"study-{answer}-{index}"
                items.append({
                    "id": card_id, "tier": "study", "written": True, "context_ready": True,
                    "claim": "People make different choices after receiving different information.",
                    "method": "60 adults read one of two short descriptions and then made a choice.",
                })
                reveals[card_id] = {"id": card_id, "answer": answer}
        # This fifth successful study has an answer but no usable experiment explanation, so it cannot
        # satisfy a daily quota by accident.
        items.append({"id": "study-successful-thin", "tier": "study", "written": True,
                      "context_ready": False, "claim": "A bare claim.", "method": None})
        reveals["study-successful-thin"] = {"id": "study-successful-thin", "answer": "successful"}
        for answer in ("successful", "failed"):
            card_id = f"famous-{answer}"
            items.append({
                "id": card_id, "tier": "famous", "written": True, "context_ready": True,
                "claim": "People make different choices after receiving different information.",
                "method": "60 adults read one of two short descriptions and then made a choice.",
            })
            reveals[card_id] = {"id": card_id, "answer": answer}

        with self.assertRaisesRegex(ValueError, "study/successful"):
            _daily_decks(items, reveals)


if __name__ == "__main__":
    unittest.main()
