import unittest
from unittest.mock import patch
import main


SAMPLE_PAPER = {
    "title": "Daily Paper",
    "abstract": "Interesting findings.",
    "year": 2025,
    "source": "ICLR",
    "url": "https://arxiv.org/abs/2501.00001",
    "citation_count": 150,
    "reason": "top conference paper",
    "score": 7.5,
}


class TestMain(unittest.TestCase):
    @patch("main.mailer.send_email")
    @patch("main.mailer.build_email")
    @patch("main.scorer.score_and_rank")
    @patch("main.fetcher.fetch_all_papers")
    def test_main_happy_path(self, mock_fetch, mock_score, mock_build, mock_send):
        mock_fetch.return_value = [SAMPLE_PAPER]
        mock_score.return_value = [SAMPLE_PAPER]
        mock_build.return_value = "<html>Email</html>"

        main.main()

        mock_fetch.assert_called_once()
        mock_score.assert_called_once()
        mock_build.assert_called_once_with(SAMPLE_PAPER)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        subject = call_args[0][1]
        self.assertIn("Daily Paper", subject)
        self.assertIn("ICLR", subject)

    @patch("main.mailer.send_email")
    @patch("main.mailer.build_email")
    @patch("main.scorer.score_and_rank")
    @patch("main.fetcher.fetch_all_papers")
    def test_main_no_papers_found(self, mock_fetch, mock_score, mock_build, mock_send):
        mock_fetch.return_value = []
        mock_score.return_value = []

        main.main()

        mock_send.assert_not_called()

    @patch("main.mailer.send_email")
    @patch("main.mailer.build_email")
    @patch("main.scorer.score_and_rank")
    @patch("main.fetcher.fetch_all_papers")
    def test_main_subject_truncated_long_title(self, mock_fetch, mock_score, mock_build, mock_send):
        long_paper = dict(SAMPLE_PAPER)
        long_paper["title"] = "A" * 200
        mock_fetch.return_value = [long_paper]
        mock_score.return_value = [long_paper]
        mock_build.return_value = "<html>Email</html>"

        main.main()

        subject = mock_send.call_args[0][1]
        self.assertLess(len(subject), 150)


if __name__ == "__main__":
    unittest.main()
