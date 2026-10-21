"""Regression checks for written feed posts and the paper-level cards built from them."""
from __future__ import annotations

import unittest

from pipeline import posts
from pipeline.game import _paper_items

GOOD = ("Half the people were given a coffee mug and half were not. Then everyone could buy and sell mugs. "
        "The people who had a mug asked for more money to sell it than the others were willing to pay to buy it.")


def record(post: str, pid: str = "g123456789") -> dict:
    return {"id": pid, "post": post}


class PostRulesTests(unittest.TestCase):
    def test_a_plain_post_passes(self):
        self.assertEqual(posts.problems(record(GOOD)), [])

    def test_the_finding_is_the_last_sentence(self):
        story, finding = posts.split(GOOD)
        self.assertTrue(finding.startswith("The people who had a mug"))
        self.assertEqual(story, "Half the people were given a coffee mug and half were not. Then everyone could buy and sell mugs.")

    def test_a_post_may_not_open_with_a_head_count_or_in_this_study(self):
        self.assertTrue(posts.problems(record("152 people were made to feel unsure. Then they rated themselves. The unsure ones wanted less change.")))
        self.assertTrue(posts.problems(record("In this study, people were given a mug. Then they traded mugs. Owners asked for more money than buyers offered.")))

    def test_a_post_may_not_mention_a_later_study(self):
        bad = GOOD.replace("Then everyone could buy and sell mugs.", "A later study replicated this with mugs.")
        self.assertTrue(any("leaks" in p for p in posts.problems(record(bad))))

    def test_statistics_and_citations_are_refused(self):
        self.assertTrue(any("statistic" in p for p in posts.problems(record(GOOD + " The effect was large (p < .01)."))))
        self.assertTrue(any("cites" in p for p in posts.problems(record(GOOD.replace("Half", "Smith et al. found that half")))))

    def test_one_sentence_is_not_a_post(self):
        self.assertTrue(posts.problems(record("People who own a mug ask for more money to sell it than others will pay to buy it, which is a long single sentence about mugs.")))

    def test_a_post_is_short(self):
        long = " ".join(["People did one more thing with the mugs before they traded them with each other."] * 5)
        self.assertTrue(any("sentences" in p or "words" in p or "characters" in p for p in posts.problems(record(long))))

    def test_stock_openers_are_refused(self):
        for opener in ("Researchers looked at how people trade mugs.", "The study looked at how people trade mugs.",
                       "This is a book chapter about mugs."):
            self.assertTrue(any("opens with" in p for p in posts.problems(record(opener + " People who had a mug asked for more money than buyers offered."))), opener)

    def test_paper_ids_are_stable_and_distinct_from_study_ids(self):
        self.assertEqual(posts.paper_id("10.1/abc"), posts.paper_id("10.1/abc"))
        self.assertTrue(posts.paper_id("10.1/abc").startswith("p"))


def synthetic(outcomes: list[str]) -> dict:
    attempts = {f"a{i}": {"id": f"a{i}", "type": "replication", "outcome": o, "rows": [], "authors_r": "Lee",
                          "year_r": 2020, "journal_r": "J Test", "doi_r": f"10.1/r{i}", "quote": "We found it again."}
                for i, o in enumerate(outcomes)}
    return {"attempts": attempts,
            "findings": {"10.1/orig": {"slug": "orig-paper", "attempts": list(attempts)}},
            "papers": {"10.1/orig": {"title": "Mugs and prices", "authors": "Smith", "year": 2010, "journal": "J Test"}}}


class PaperCardTests(unittest.TestCase):
    pid = posts.paper_id("10.1/orig")

    def build(self, outcomes, covered=frozenset(), have_post=True):
        items, reveals = [], {}
        made = _paper_items(synthetic(outcomes), items, reveals, {self.pid: {"post": GOOD}} if have_post else {}, set(covered), set())
        return made, items, reveals

    def test_a_unanimous_pair_with_a_post_becomes_a_card(self):
        made, items, reveals = self.build(["successful", "successful"])
        self.assertEqual(made, 1)
        self.assertEqual(items[0]["id"], self.pid)
        self.assertEqual(items[0]["tier"], "study")
        self.assertEqual(items[0]["claim"], posts.split(GOOD)[1])
        self.assertNotIn("answer", items[0])
        self.assertEqual(reveals[self.pid]["answer"], "successful")
        self.assertEqual(reveals[self.pid]["finding"], "orig-paper")
        self.assertEqual(len(reveals[self.pid]["replications"]), 2)

    def test_disagreeing_or_unclear_attempts_make_no_card(self):
        self.assertEqual(self.build(["successful", "failed"])[0], 0)
        self.assertEqual(self.build(["inconclusive"])[0], 0)
        self.assertEqual(self.build(["mixed"])[0], 0)

    def test_a_paper_with_study_level_rows_is_not_dealt_twice(self):
        self.assertEqual(self.build(["failed"], covered={"10.1/orig"})[0], 0)

    def test_no_post_no_card(self):
        self.assertEqual(self.build(["failed"], have_post=False)[0], 0)


class DedupeAfterPostsTests(unittest.TestCase):
    def test_a_post_does_not_bring_back_a_card_dropped_as_a_duplicate(self):
        from pipeline.game import _dedupe_claims
        same = "Reminding people of scarce resources makes them find more novel uses."
        items = [{"id": "gstudy", "tier": "study", "claim": "People reminded of scarcity found more novel uses.", "_dedupe_key": same},
                 {"id": "ffamous", "tier": "famous", "claim": same}]
        reveals = {"gstudy": {"answer": "successful"}, "ffamous": {"answer": "successful"}}
        _dedupe_claims(items, reveals)
        self.assertEqual([i["id"] for i in items], ["gstudy"])
        self.assertNotIn("ffamous", reveals)
        self.assertNotIn("_dedupe_key", items[0])


class CardHoldTests(unittest.TestCase):
    def test_held_ids_are_read_and_a_missing_file_holds_nothing(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock

        from pipeline import load
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "card_holds.json"
            with mock.patch.object(load, "CARD_HOLDS", p):
                self.assertEqual(load.load_card_holds(), set())
                p.write_text(json.dumps({"holds": {"g1": {"reason": "x"}, "f2": {"reason": "y"}}}), encoding="utf-8")
                self.assertEqual(load.load_card_holds(), {"g1", "f2"})


if __name__ == "__main__":
    unittest.main()
