"""Contracts for the answer-separated, balanced daily game schedule."""

from __future__ import annotations

import unittest

from pipeline.export import _daily_decks, _finding_reveal, has_local_page
from pipeline.game import attach_finding_contexts, context_ready


class DailyGameExportTests(unittest.TestCase):
    def test_every_addressable_finding_gets_a_local_prediction_page(self) -> None:
        self.assertTrue(has_local_page({"slug": "a-thin-but-addressable-finding"}))
        self.assertFalse(has_local_page({"slug": ""}))

    def test_finding_answer_is_a_separate_minimal_reveal_payload(self) -> None:
        finding = {
            "doi_o": "10.1234/original",
            "attempts": ["answer-bearing-attempt"],
            "lenses": {"record": {
                "code": "single_success", "label": "Replicated once", "k": 1,
                "n_attempts": 1, "successful": 1, "mixed": 0, "failed": 0,
                "inconclusive": 0, "not_coded": 0,
            }},
        }
        payload = _finding_reveal(finding)
        self.assertEqual(payload, {
            "schema_version": 1,
            "record": {
                "code": "single_success", "label": "Replicated once",
                "n_attempts": 1, "successful": 1, "mixed": 0, "failed": 0,
            },
        })
        self.assertNotIn("attempts", payload)
        self.assertNotIn("doi_o", payload)

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

    def test_safe_game_context_can_be_reused_without_answer_or_card_identity(self) -> None:
        item = {
            "id": "study-successful-secret", "tier": "study", "written": True, "context_ready": True,
            "claim": "People make different choices after receiving different information.",
            "method": "60 adults read one of two short descriptions and then made a choice.",
            "cues": {"p": "p ≤ .005"},
        }
        graph = {"findings": {"10.1234/original": {"slug": "original-finding"}}}
        count = attach_finding_contexts(graph, [item], {
            item["id"]: {"answer": "successful", "finding": "original-finding"},
        })
        self.assertEqual(count, 1)
        contexts = graph["findings"]["10.1234/original"]["game_contexts"]
        self.assertEqual(contexts, [{
            "claim": item["claim"], "method": item["method"],
            "review_state": "plain_language_game_context_not_source_reviewed",
        }])
        rendered = str(contexts)
        self.assertNotIn("successful", rendered)
        self.assertNotIn(item["id"], rendered)
        self.assertNotIn("p ≤ .005", rendered)

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
