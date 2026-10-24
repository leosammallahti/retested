import unittest

from pipeline import registry


class AuthorNameTests(unittest.TestCase):
    def test_a_group_tag_is_not_taken_for_the_first_author(self):
        raw = '[{"given": "", "family": "[SCORE]"}, {"given": "Ann", "family": "Parsons"}, {"given": "B", "family": "Lee"}, {"given": "C", "family": "Kim"}]'
        self.assertEqual(registry._short(raw), "Parsons et al.")

    def test_a_crossref_author_list_from_a_reviewed_record_is_shortened(self):
        raw = '[{"given":"Nitika","family":"Garg","sequence":"first"},{"given":"J. Jeffrey","family":"Inman","sequence":"additional"}]'
        self.assertEqual(registry._names(raw), "Garg & Inman")

    def test_a_plain_author_string_stays_as_written(self):
        self.assertEqual(registry._names("Bailey, LaFrance & Dovidio"), "Bailey, LaFrance & Dovidio")
        self.assertIsNone(registry._names(None))


if __name__ == "__main__":
    unittest.main()
