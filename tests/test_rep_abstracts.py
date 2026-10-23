"""Checks for the later papers' abstracts harvested from the caches."""
from __future__ import annotations

import unittest

from pipeline import rep_abstracts as ra


class TitleMatchTests(unittest.TestCase):
    def test_the_same_paper_with_different_punctuation_and_subtitle_matches(self):
        self.assertTrue(ra.title_matches("The stability of working memory: Do previous tasks influence complex span?",
                                         "The stability of working memory: do previous tasks influence complex span"))

    def test_another_papers_abstract_is_refused(self):
        self.assertFalse(ra.title_matches("Self-control as a limited resource", "A multilab preregistered replication of ego depletion"))

    def test_a_missing_title_never_matches(self):
        self.assertFalse(ra.title_matches(None, "A title"))
        self.assertFalse(ra.title_matches("A title", ""))


class CleanTests(unittest.TestCase):
    def test_publisher_footers_and_markup_are_removed(self):
        raw = "<jats:p>We tested people.</jats:p> They did better. (PsycINFO Database Record (c) 2011 APA, all rights reserved)."
        self.assertEqual(ra.clean(raw), "We tested people. They did better.")

    def test_an_inverted_index_is_put_back_in_order(self):
        self.assertEqual(ra._rebuild({"people": [1], "We": [0], "tested": [2]}), "We people tested")


if __name__ == "__main__":
    unittest.main()
