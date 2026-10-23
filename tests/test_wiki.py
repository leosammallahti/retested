"""Regression checks for the wiki story: text hygiene, what a page may claim, and which pages carry the new template."""
from __future__ import annotations

import unittest
from collections import Counter

from pipeline import game, wiki


def attempt(**kw) -> dict:
    base = {"id": "at_1", "doi_o": "10.1/o", "type": "replication", "outcome": "failed", "year_r": 2015, "authors_r": "Smith & Jones",
            "title_r": "A title", "rows": [], "legacy_rows": [], "sources": ["flora"], "outcomes_by_source": {"flora": "failed"},
            "sources_disagree": False}
    base.update(kw)
    return base


class TextHygieneTests(unittest.TestCase):
    def test_line_break_hyphens_are_healed_but_real_hyphens_stay(self):
        vocab = Counter({"control": 3, "depletion": 2})
        self.assertEqual(wiki.tidy("con- trol of the ego- depletion effect", vocab), "control of the ego-depletion effect")

    def test_a_quote_joined_from_several_rows_is_shown_once(self):
        q = "Only this. || Only this. || Only this. However, a second sentence."
        self.assertEqual(wiki.dedupe_quote(q), "Only this. However, a second sentence.")

    def test_a_coding_note_is_not_the_replicators_words(self):
        a = attempt(quote="Coded as not replicated: Replicate = 0")
        self.assertEqual(wiki.attempt_story(a, Counter(), {}, None)["their_words"], "")

    def test_a_coders_column_note_is_not_the_replicators_words(self):
        for q in ("mixed as not both columns 1 or 0", "NB: SCORE relied on statistical significance and direction."):
            self.assertEqual(wiki.attempt_story(attempt(quote=q), Counter(), {}, None)["their_words"], "")

    def test_the_reviewed_outcome_quote_wins_over_the_database_quote(self):
        a = attempt(quote="Some discussion text.", retested_review={"outcome_quote": "We found no effect of the drink.", "reviewed_on": "2026-09-25"})
        self.assertEqual(wiki.attempt_story(a, Counter(), {}, None)["their_words"], "We found no effect of the drink.")

    def test_reviewer_bookkeeping_is_dropped_and_study_description_kept(self):
        note = ("The later team ran 200 new participants with the same video task. Cached OpenAlex W123456789 primary Psychology. "
                "Successful is narrowly scoped to the first outcome. Feltz and Kerr authored both.")
        self.assertEqual(wiki.review_sentences(note), ["The later team ran 200 new participants with the same video task."])

    def test_a_written_explanation_shows_only_for_the_paper_it_was_written_from(self):
        a = attempt(doi_r="10.1/r", retested_review={"review_note": "The later team ran 200 new participants with the same video task."})
        ex = {"at_1": {"doi_r": "10.1/r", "did": "People watched a video.", "found": "No effect.", "basis": "the later paper's abstract"}}
        s = wiki.attempt_story(a, Counter(), {"at_1": {"line": "A hand line."}}, None, ex)
        self.assertEqual((s["did"], s["found"], s["line"], s["reviewer_sentences"]), ("People watched a video.", "No effect.", None, []))
        self.assertEqual(s["written_check"], "sampled")       # no read_on: the page must not say it was read
        ex["at_1"]["read_on"] = "2026-10-22"
        self.assertEqual(wiki.attempt_story(a, Counter(), {}, None, ex)["written_check"], "read")
        moved = wiki.attempt_story(attempt(doi_r="10.1/other"), Counter(), {}, None, ex)
        self.assertIsNone(moved["did"])
        half = wiki.attempt_story(a, Counter(), {}, None, {"at_1": {"doi_r": "10.1/r", "did": "People watched a video.", "found": ""}})
        self.assertIsNone(half["did"])

    def test_a_long_list_of_authors_is_shortened(self):
        self.assertEqual(wiki.short_authors("Xiaomeng Xu, Kathryn Demos, Tricia Leahey, Chantelle Hart 2014"), "Xu et al.")
        self.assertEqual(wiki.short_authors("Kidd & Castano"), "Kidd & Castano")


class WhatAPageMayClaimTests(unittest.TestCase):
    def test_a_size_from_several_rows_or_the_legacy_file_is_not_shown(self):
        self.assertEqual(wiki._n_of(attempt(est={"n": 48, "k_rows": 7, "legacy": True})), None)
        self.assertEqual(wiki._n_of(attempt(est={"n": 200, "k_rows": 1, "legacy": False})), 200)

    def test_shared_authors_are_claimed_only_when_two_surnames_match(self):
        orig = {"surnames": ["kidd", "castano"]}
        self.assertTrue(wiki.shares_author(attempt(authors_r="Kidd & Castano"), orig))
        self.assertFalse(wiki.shares_author(attempt(authors_r="Wang et al."), {"surnames": ["wang", "lee"]}))

    def test_the_original_size_is_stated_only_when_one_number_stands_for_it(self):
        one = [attempt(rows=[{"n_o": 141, "n_r": 200}], est={"n": 200, "k_rows": 1})]
        two = [attempt(rows=[{"n_o": 80, "n_r": 300}, {"n_o": 356, "n_r": 370}])]
        a1 = [wiki.attempt_story(a, Counter(), {}, None) for a in one]
        a2 = [wiki.attempt_story(a, Counter(), {}, None) for a in two]
        self.assertTrue(any("141" in w["text"] for w in wiki._group_why(one, a1)))
        self.assertFalse(any(w["kind"] == "size" for w in wiki._group_why(two, a2)))

    def test_a_single_attempt_without_a_verdict_is_not_called_the_only_attempt(self):
        rec = {"code": "single_failure", "label": "Failed once", "successful": 0, "failed": 1, "mixed": 0, "inconclusive": 0, "not_coded": 1}
        v = wiki.verdict_story(rec, [attempt(), attempt(id="at_2", outcome="not_coded")])
        self.assertIn("with a clear verdict", v["headline"])
        self.assertIn("1 has no clear verdict yet", v["detail"])

    def test_the_headline_never_changes_the_records_code(self):
        for code, text in wiki.HEADLINE.items():
            rec = {"code": code, "label": "x", "successful": 0, "failed": 0, "mixed": 0, "inconclusive": 0, "not_coded": 0}
            self.assertEqual(wiki.verdict_story(rec, [])["code"], code)
            self.assertTrue(text.endswith("."))


class ReleaseTests(unittest.TestCase):
    def test_only_pages_with_a_reviewed_post_carry_the_new_template(self):
        doc = {"schema_version": 1,
               "effects": {"a": {"scenes": [{"id": "g1"}], "groups": []}, "b": {"scenes": [], "groups": [{"scenes": []}]},
                           "c": {"scenes": [], "groups": [{"scenes": [{"id": "g2"}]}]}},
               "findings": {"x": {"scenes": [{"id": "g1"}]}, "y": {"scenes": []}}}
        out = wiki.released(doc)
        self.assertEqual(sorted(out["effects"]), ["a", "c"])
        self.assertEqual(sorted(out["findings"]), ["x"])

    def test_a_scene_is_answer_blind_by_the_decks_own_leak_test(self):
        post = {"post": "People played a putting game. Some were told the ball was lucky. People did better with the ball they believed was lucky."}
        scene = wiki._scene("g1", {"g1": post}, None)
        self.assertFalse(game.LEAK.search(scene["did"] + " " + scene["found"]))

    def test_a_held_card_gives_no_scene(self):
        f = {"attempts": ["at_1"]}
        att = {"at_1": attempt(rows=[{"study_o": "1"}])}
        pid = wiki._gid("10.1/o", "1")
        posts = {pid: {"post": "People did a thing. Then they did another thing. They did better."}}
        self.assertEqual(len(wiki.finding_scenes("10.1/o", f, att, posts, set(), Counter())), 1)
        self.assertEqual(wiki.finding_scenes("10.1/o", f, att, posts, {pid}, Counter()), [])


if __name__ == "__main__":
    unittest.main()
