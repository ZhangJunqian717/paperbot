import unittest
import os
from unittest.mock import patch, MagicMock
import mailer


SAMPLE_PAPER = {
    "title": "Test Paper Title",
    "abstract": "This is a test abstract for the paper.",
    "year": 2025,
    "source": "NeurIPS",
    "url": "https://arxiv.org/abs/2501.00001",
    "citation_count": 250,
    "reason": "well-cited paper",
}


class TestBuildEmail(unittest.TestCase):
    def test_build_email_contains_key_elements(self):
        html = mailer.build_email(SAMPLE_PAPER)

        self.assertIn("Test Paper Title", html)
        self.assertIn("This is a test abstract", html)
        self.assertIn("NeurIPS", html)
        self.assertIn("2025", html)
        self.assertIn("https://arxiv.org/abs/2501.00001", html)
        self.assertIn("250", html)
        self.assertIn("well-cited paper", html)
        self.assertIn("PaperBot", html)

    def test_build_email_is_valid_html(self):
        html = mailer.build_email(SAMPLE_PAPER)
        self.assertTrue("<html" in html)
        self.assertTrue("</html>" in html)


class TestSendEmail(unittest.TestCase):
    @patch("mailer.smtplib.SMTP")
    def test_send_email_connects_and_sends(self, mock_smtp_class):
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        with patch.dict(os.environ, {
            "SMTP_SERVER": "smtp.test.com",
            "SMTP_PORT": "587",
            "SMTP_EMAIL": "sender@test.com",
            "SMTP_PASSWORD": "secret",
            "RECIPIENT_EMAIL": "receiver@test.com",
        }):
            mailer.send_email("<html>Test</html>", "Subject Line")

        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("sender@test.com", "secret")
        mock_smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
