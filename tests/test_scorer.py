import unittest
import scorer


class TestScorer(unittest.TestCase):
    def test_survey_paper_gets_bonus(self):
        papers = [
            {
                "title": "A Comprehensive Survey of Large Language Models",
                "abstract": "We review...",
                "year": 2025,
                "source": "arXiv",
                "citation_count": 10,
                "url": "http://x"
            },
            {
                "title": "A Novel Activation Function for Small Networks",
                "abstract": "We propose...",
                "year": 2025,
                "source": "arXiv",
                "citation_count": 3,
                "url": "http://y"
            },
        ]
        ranked = scorer.score_and_rank(papers)
        best = ranked[0]
        self.assertIn("survey", best["title"].lower())
        self.assertIn("survey", best["reason"].lower())

    def test_high_citation_gets_bonus(self):
        papers = [
            {"title": "Paper Low", "abstract": "...", "year": 2025, "source": "arXiv", "citation_count": 5, "url": "x"},
            {"title": "Paper High", "abstract": "...", "year": 2025, "source": "arXiv", "citation_count": 5000, "url": "y"},
        ]
        ranked = scorer.score_and_rank(papers)
        best = ranked[0]
        self.assertEqual(best["title"], "Paper High")
        self.assertIn("landmark", best["reason"].lower())

    def test_old_non_landmark_filtered_out(self):
        papers = [
            {"title": "Old Paper", "abstract": "old", "year": 2018, "source": "arXiv", "citation_count": 50, "url": "x"},
            {"title": "New Paper", "abstract": "new", "year": 2025, "source": "arXiv", "citation_count": 1, "url": "y"},
        ]
        ranked = scorer.score_and_rank(papers)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["title"], "New Paper")

    def test_old_landmark_kept(self):
        papers = [
            {
                "title": "Deep Residual Learning",
                "abstract": "...",
                "year": 2016,
                "source": "CVPR",
                "citation_count": 100000,
                "url": "x"
            },
        ]
        ranked = scorer.score_and_rank(papers)
        self.assertEqual(len(ranked), 1)
        self.assertIn("landmark", ranked[0]["reason"].lower())

    def test_top_n_returned(self):
        papers = [
            {"title": f"Paper {i}", "abstract": f"Abstract {i}", "year": 2025, "source": "arXiv", "citation_count": i * 10, "url": "u"}
            for i in range(10)
        ]
        ranked = scorer.score_and_rank(papers, top_n=3)
        self.assertEqual(len(ranked), 3)

    def test_top_conference_bonus(self):
        papers = [
            {"title": "NeurIPS Winner", "abstract": "Some abstract", "year": 2025, "source": "NeurIPS", "citation_count": 5, "url": "x"},
            {"title": "ArXiv Only", "abstract": "Some abstract", "year": 2025, "source": "arXiv", "citation_count": 5, "url": "y"},
        ]
        ranked = scorer.score_and_rank(papers)
        self.assertEqual(ranked[0]["title"], "NeurIPS Winner")

    def test_empty_input(self):
        ranked = scorer.score_and_rank([])
        self.assertEqual(ranked, [])


if __name__ == "__main__":
    unittest.main()
