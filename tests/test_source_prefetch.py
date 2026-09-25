"""Focused checks for primary-text classification."""
import unittest

from pipeline.source_prefetch import _jina_has_full_article


class JinaArticleTests(unittest.TestCase):
    def test_navigation_and_abstract_are_not_full_text(self):
        shell = "Markdown Content:\n# Journal\n" + ("navigation link\n" * 600) + "## Abstract\nA study result."
        self.assertFalse(_jina_has_full_article(shell))

    def test_article_with_methods_and_results_is_full_text(self):
        article = "Markdown Content:\n## Introduction\n" + ("Background text. " * 180) + "\n## Methods\n" + ("Methods text. " * 180) + "\n## Results\n" + ("Observed findings. " * 180)
        self.assertTrue(_jina_has_full_article(article))


if __name__ == "__main__":
    unittest.main()
