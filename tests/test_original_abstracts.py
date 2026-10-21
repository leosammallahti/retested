"""Regression checks for the gate every kept original abstract must pass."""
from __future__ import annotations

import unittest

from pipeline.original_abstracts import clean, reject_reason

REAL = ("Participants read a short story about a person who found a wallet and then rated how honest the person was. "
        "Some read a version in which the wallet was returned, others one in which it was kept. Honesty ratings were "
        "collected on a nine point scale after a short delay, and the order of the two versions was varied across "
        "participants so that neither version always came first in the session.")


class OriginalAbstractGateTests(unittest.TestCase):
    def test_a_real_abstract_passes(self):
        self.assertIsNone(reject_reason(REAL, "Honesty and wallets", "Honesty and wallets"))

    def test_short_text_is_not_an_abstract(self):
        self.assertEqual(reject_reason("Too short to be one."), "too short")

    def test_citation_and_download_lines_are_rejected(self):
        junk = "[16] God Is Watching You Priming God Concepts Increases Prosocial Behavior in an Anonymous Economic Game " * 4
        self.assertEqual(reject_reason(junk), "not an abstract")
        counters = "1,510 Metrics Total Downloads 1,510 Last 6 Months 212 Last 12 Months 387 " * 6
        self.assertEqual(reject_reason(counters), "not an abstract")

    def test_non_english_text_is_rejected(self):
        german = ("Die vorliegende Untersuchung prüft, ob Menschen bei der Entscheidung zwischen mehreren Optionen "
                  "systematisch dazu neigen, die zuerst genannte Möglichkeit zu bevorzugen, und zwar unabhängig "
                  "von deren tatsächlichem Wert für die Befragten in dieser Studie, wie die Ergebnisse zeigen. ") * 2
        self.assertEqual(reject_reason(german), "not English")

    def test_a_doi_that_resolves_to_another_paper_is_rejected(self):
        self.assertEqual(reject_reason(REAL, "Honesty and wallets", "Glacier retreat in the Alps since 1850"), "title mismatch")

    def test_a_missing_title_does_not_block_a_doi_matched_abstract(self):
        self.assertIsNone(reject_reason(REAL, "Honesty and wallets", None))

    def test_clean_strips_markup_and_the_abstract_label(self):
        self.assertEqual(clean("<jats:p>Abstract: People   read <i>stories</i>.</jats:p>"), "People read stories.")


if __name__ == "__main__":
    unittest.main()
