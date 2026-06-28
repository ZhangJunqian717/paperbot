import unittest
from unittest.mock import patch, MagicMock
import fetcher


class TestArxivFetch(unittest.TestCase):
    @patch("fetcher.requests.get")
    def test_fetch_arxiv_parses_atom_xml(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test Paper Title</title>
    <summary>This is a test abstract.</summary>
    <published>2025-01-15T00:00:00Z</published>
    <id>http://arxiv.org/abs/2501.00001v1</id>
  </entry>
</feed>"""
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        papers = fetcher.fetch_arxiv_papers(max_results=10)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "Test Paper Title")
        self.assertEqual(papers[0]["abstract"], "This is a test abstract.")
        self.assertEqual(papers[0]["year"], 2025)
        self.assertEqual(papers[0]["url"], "https://arxiv.org/abs/2501.00001")
        self.assertEqual(papers[0]["source"], "arXiv")

    @patch("fetcher.requests.get")
    def test_fetch_arxiv_handles_errors(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        papers = fetcher.fetch_arxiv_papers(max_results=10)
        self.assertEqual(papers, [])


class TestSemanticFetch(unittest.TestCase):
    @patch("fetcher.requests.get")
    def test_fetch_semantic_parses_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "Attention Is All You Need",
                    "abstract": "Transformer architecture paper.",
                    "year": 2024,
                    "citationCount": 500,
                    "venue": "NeurIPS",
                    "externalIds": {"ArXiv": "1706.03762"}
                }
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        papers = fetcher.fetch_semantic_papers(limit=10)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "Attention Is All You Need")
        self.assertEqual(papers[0]["citation_count"], 500)
        self.assertEqual(papers[0]["source"], "NeurIPS")


class TestFetchAll(unittest.TestCase):
    @patch("fetcher.fetch_semantic_papers")
    @patch("fetcher.fetch_arxiv_papers")
    def test_merge_deduplicates_by_title(self, mock_arxiv, mock_semantic):
        mock_arxiv.return_value = [
            {"title": "Paper A", "year": 2025, "source": "arXiv", "url": "http://a", "abstract": "abs a"}
        ]
        mock_semantic.return_value = [
            {"title": "Paper A", "year": 2025, "source": "NeurIPS", "url": "http://a", "abstract": "abs a", "citation_count": 100},
            {"title": "Paper B", "year": 2025, "source": "ICML", "url": "http://b", "abstract": "abs b", "citation_count": 50},
        ]

        papers = fetcher.fetch_all_papers()

        self.assertEqual(len(papers), 2)
        titles = {p["title"] for p in papers}
        self.assertEqual(titles, {"Paper A", "Paper B"})


if __name__ == "__main__":
    unittest.main()
