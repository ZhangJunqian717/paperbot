# PaperBot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that fetches recent AI papers from arXiv + Semantic Scholar, scores them for freshman-friendliness, and emails the best one daily via GitHub Actions.

**Architecture:** Four independent modules (fetcher, scorer, mailer, main) glued by a simple pipeline. Stateless — each run fetches fresh, scores, sends one email. Deployed on GitHub Actions with a daily cron trigger.

**Tech Stack:** Python 3.13, `requests`, `smtplib`/`email` (stdlib), GitHub Actions

## Global Constraints

- Python 3.13+
- English-only paper content (original abstracts)
- Paper year ≥ 2022 unless citations > 5000
- One email per run, one paper per email
- All secrets via environment variables (GitHub Secrets in prod)
- No paid API keys required
- No database — fully stateless

---

### Task 1: Project skeleton and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Produces: `requirements.txt` with exact dependencies
- Produces: `.env.example` as template for required env vars
- Produces: `.gitignore` excluding `.env`, `__pycache__`, etc.

- [ ] **Step 1: Write `requirements.txt`**

```txt
requests>=2.32.0
pytest>=8.0.0
```

- [ ] **Step 2: Write `.env.example`**

```ini
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password
RECIPIENT_EMAIL=your-email@gmail.com
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Success.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "chore: add project skeleton and dependencies"
```

---

### Task 2: Fetcher module — arXiv API

**Files:**
- Create: `fetcher.py`
- Test: `tests/test_fetcher.py`

**Interfaces:**
- Produces: `fetch_arxiv_papers(max_results: int = 50) -> list[dict]`
  - Each dict: `{"title": str, "abstract": str, "year": int, "url": str, "source": str}`
- Produces: `fetch_semantic_papers(query: str = "artificial intelligence", limit: int = 20) -> list[dict]`
  - Each dict: `{"title": str, "abstract": str, "year": int, "url": str, "source": str, "citation_count": int}`
- Produces: `fetch_all_papers() -> list[dict]` — merges both sources, deduplicates by title

- [ ] **Step 1: Write the failing test**

Create `tests/test_fetcher.py`:

```python
import unittest
from unittest.mock import patch, MagicMock
import fetcher


class TestArxivFetch(unittest.TestCase):
    @patch("fetcher.requests.get")
    def test_fetch_arxiv_parses_atom_xml(self, mock_get):
        # Simulate arXiv Atom XML response
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fetcher.py -v`
Expected: FAIL (no module `fetcher`)

- [ ] **Step 3: Write `fetcher.py`**

```python
"""Fetcher: retrieve recent AI papers from arXiv and Semantic Scholar."""
import re
import xml.etree.ElementTree as ET
import requests

ARXIV_API = "http://export.arxiv.org/api/query"
SEMANTIC_API = "https://api.semanticscholar.org/graph/v1/paper/search"
REQUEST_TIMEOUT = 30


def fetch_arxiv_papers(max_results: int = 50) -> list[dict]:
    """Fetch recent papers from arXiv cs.AI, cs.LG, cs.CL, cs.CV categories."""
    categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
    query = "+OR+".join(f"cat:{c}" for c in categories)
    url = (
        f"{ARXIV_API}?search_query={query}"
        f"&sortBy=submittedDate&sortOrder=descending"
        f"&start=0&max_results={max_results}"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception:
        return []

    papers = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        id_el = entry.find("atom:id", ns)

        title = title_el.text.strip() if title_el is not None else ""
        # Remove newlines and extra whitespace from title
        title = " ".join(title.split())

        abstract = summary_el.text.strip() if summary_el is not None else ""
        abstract = " ".join(abstract.split())

        year = 0
        if published_el is not None and published_el.text:
            m = re.match(r"(\d{4})", published_el.text)
            if m:
                year = int(m.group(1))

        arxiv_url = ""
        if id_el is not None and id_el.text:
            arxiv_id = id_el.text.strip()
            # Convert http://arxiv.org/abs/XXXX to https://arxiv.org/abs/XXXX
            arxiv_url = arxiv_id.replace("http://", "https://").rstrip("v1234567890")

        if title and abstract:
            papers.append({
                "title": title,
                "abstract": abstract,
                "year": year,
                "url": arxiv_url,
                "source": "arXiv",
            })
    return papers


def fetch_semantic_papers(query: str = "artificial intelligence", limit: int = 20) -> list[dict]:
    """Fetch papers from Semantic Scholar API with citation and venue data."""
    url = (
        f"{SEMANTIC_API}?"
        f"query={requests.utils.quote(query)}"
        f"&fields=title,abstract,year,citationCount,venue,externalIds,url"
        f"&limit={limit}"
        f"&sort=citationCount:desc"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    papers = []
    for item in data.get("data", []):
        title = (item.get("title") or "").strip()
        title = " ".join(title.split())
        abstract = (item.get("abstract") or "").strip()
        abstract = " ".join(abstract.split())
        year = item.get("year") or 0
        citation_count = item.get("citationCount") or 0
        venue = item.get("venue", "") or ""

        # Source: prefer proper venue name, fall back to plain text
        source = venue if venue else "Unknown"

        paper_url = item.get("url", "")
        # Prefer arXiv link
        ext_ids = item.get("externalIds") or {}
        if ext_ids.get("ArXiv"):
            paper_url = f"https://arxiv.org/abs/{ext_ids['ArXiv']}"

        if title:
            papers.append({
                "title": title,
                "abstract": abstract,
                "year": year,
                "url": paper_url,
                "source": source,
                "citation_count": citation_count,
            })
    return papers


def _normalize_title(title: str) -> str:
    """Normalize a title for deduplication comparison."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def fetch_all_papers() -> list[dict]:
    """Fetch papers from all sources, merge, and deduplicate."""
    arxiv = fetch_arxiv_papers(max_results=50)
    semantic = fetch_semantic_papers(limit=20)

    seen = set()
    merged = []

    # Semantic Scholar first (richer metadata — venue, citations)
    for p in semantic:
        key = _normalize_title(p["title"])
        if key not in seen:
            seen.add(key)
            merged.append(p)

    # arXiv supplements, deduplicating against Semantic Scholar
    for p in arxiv:
        key = _normalize_title(p["title"])
        if key not in seen:
            seen.add(key)
            p.setdefault("citation_count", 0)
            merged.append(p)

    return merged
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fetcher.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_fetcher.py fetcher.py
git commit -m "feat: add fetcher module — arXiv + Semantic Scholar APIs"
```

---

### Task 3: Scorer module

**Files:**
- Create: `scorer.py`
- Test: `tests/test_scorer.py`

**Interfaces:**
- Consumes: `list[dict]` from `fetcher.fetch_all_papers()` (each dict has: title, abstract, year, source, citation_count, url)
- Produces: `score_and_rank(papers: list[dict], top_n: int = 1) -> list[dict]` — same dicts with `score` (float) and `reason` (str) added

- [ ] **Step 1: Write the failing test**

Create `tests/test_scorer.py`:

```python
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
        self.assertIn("citation", best["reason"].lower())

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
            {"title": f"Paper {i}", "abstract": "", "year": 2025, "source": "arXiv", "citation_count": i * 10, "url": "u"}
            for i in range(10)
        ]
        ranked = scorer.score_and_rank(papers, top_n=3)
        self.assertEqual(len(ranked), 3)

    def test_top_conference_bonus(self):
        papers = [
            {"title": "NeurIPS Winner", "abstract": "", "year": 2025, "source": "NeurIPS", "citation_count": 5, "url": "x"},
            {"title": "ArXiv Only", "abstract": "", "year": 2025, "source": "arXiv", "citation_count": 5, "url": "y"},
        ]
        ranked = scorer.score_and_rank(papers)
        self.assertEqual(ranked[0]["title"], "NeurIPS Winner")

    def test_empty_input(self):
        ranked = scorer.score_and_rank([])
        self.assertEqual(ranked, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scorer.py -v`
Expected: FAIL (no module `scorer`)

- [ ] **Step 3: Write `scorer.py`**

```python
"""Scorer: rank papers by freshman-friendliness and recency."""
import random

# Journals and conferences considered "top tier"
TOP_VENUES = {
    "neurips", "icml", "iclr", "cvpr", "aaai", "acl", "emnlp",
    "nature", "science", "nature machine intelligence",
    "nature communications", "science advances",
    "ieee transactions on pattern analysis",
    "international conference on machine learning",
    "conference on neural information processing systems",
}

# Keywords that suggest a survey/review/tutorial paper
SURVEY_KEYWORDS = ["survey", "review", "tutorial", "overview", "a comprehensive", "state of the art", "benchmark"]


def _is_survey(title: str) -> bool:
    """Check if a paper title suggests it's a survey or review."""
    lower = title.lower()
    return any(kw in lower for kw in SURVEY_KEYWORDS)


def _is_top_venue(source: str) -> bool:
    """Check if the source matches a top-tier venue."""
    lower = source.lower()
    return any(v in lower for v in TOP_VENUES)


def _score_paper(paper: dict) -> tuple[float, list[str]]:
    """Score a single paper, returning (score, reason_tags)."""
    score = 0.0
    reasons = []

    title = paper.get("title", "")
    source = paper.get("source", "")
    year = paper.get("year", 0)
    citations = paper.get("citation_count", 0)

    # Survey/review/tutorial bonus
    if _is_survey(title):
        score += 3
        reasons.append("survey/review paper — great for learning")

    # High citation bonus
    if citations > 5000:
        score += 3
        reasons.append("landmark paper — highly influential")
    elif citations > 100:
        score += 2
        reasons.append("well-cited paper")

    # Top venue bonus
    if _is_top_venue(source):
        score += 1
        reasons.append(f"from {source}")

    # Recency bonus
    if year >= 2024:
        score += 3
        reasons.append("very recent")
    elif year >= 2022:
        score += 1
        reasons.append("recent")

    # Random jitter to vary daily picks
    score += random.uniform(-0.5, 0.5)

    return score, reasons


def _should_filter(paper: dict) -> bool:
    """Decide whether to filter out a paper entirely."""
    year = paper.get("year", 0)
    citations = paper.get("citation_count", 0)
    # Filter out pre-2022 papers unless they are landmark (5000+ citations)
    if year < 2022 and citations < 5000:
        return True
    # Filter out papers with no abstract
    if not paper.get("abstract", "").strip():
        return True
    return False


def score_and_rank(papers: list[dict], top_n: int = 1) -> list[dict]:
    """Score papers, filter old/irrelevant ones, rank, and return top N."""
    # Filter first
    kept = [p for p in papers if not _should_filter(p)]

    # Score
    scored = []
    for p in kept:
        score, reasons = _score_paper(p)
        p = dict(p)  # shallow copy to avoid mutating input
        p["score"] = round(score, 2)
        p["reason"] = reasons[0] if reasons else "AI paper you might find interesting"
        scored.append(p)

    # Sort by score descending
    scored.sort(key=lambda p: p["score"], reverse=True)

    return scored[:top_n]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scorer.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_scorer.py scorer.py
git commit -m "feat: add scorer module with freshman-friendly ranking"
```

---

### Task 4: Mailer module

**Files:**
- Create: `mailer.py`
- Test: `tests/test_mailer.py`

**Interfaces:**
- Consumes: single paper dict from `scorer.score_and_rank()` (with fields: title, abstract, year, source, url, citation_count, reason)
- Produces: `build_email(paper: dict) -> str` — returns HTML string
- Produces: `send_email(html_body: str, subject: str) -> None` — sends via SMTP, raises on failure

- [ ] **Step 1: Write the failing test**

Create `tests/test_mailer.py`:

```python
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
        self.assertIn("PaperBot", html)  # branding

    def test_build_email_is_valid_html(self):
        html = mailer.build_email(SAMPLE_PAPER)
        self.assertTrue(html.startswith("<!DOCTYPE html>") or "<html" in html)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mailer.py -v`
Expected: FAIL (no module `mailer`)

- [ ] **Step 3: Write `mailer.py`**

```python
"""Mailer: build and send formatted HTML email via SMTP."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_email(paper: dict) -> str:
    """Build an HTML email body from a paper dict."""
    title = paper.get("title", "Untitled")
    abstract = paper.get("abstract", "")
    year = paper.get("year", "")
    source = paper.get("source", "Unknown")
    url = paper.get("url", "")
    citations = paper.get("citation_count", 0)
    reason = paper.get("reason", "")

    citations_str = f"{citations:,}" if citations else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
<tr>
<td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

  <!-- Header -->
  <tr>
    <td style="padding: 32px 40px 0 40px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #888; margin-bottom: 8px;">Daily AI Paper</div>
      <h1 style="margin: 0 0 8px 0; font-size: 22px; line-height: 1.35; color: #1a1a1a;">{title}</h1>
    </td>
  </tr>

  <!-- Meta -->
  <tr>
    <td style="padding: 8px 40px 20px 40px;">
      <span style="display: inline-block; background: #eef2ff; color: #4338ca; padding: 3px 10px; border-radius: 4px; font-size: 12px; margin-right: 6px;">{source}</span>
      <span style="display: inline-block; background: #f0fdf4; color: #166534; padding: 3px 10px; border-radius: 4px; font-size: 12px; margin-right: 6px;">{year}</span>
      <span style="display: inline-block; background: #fffbeb; color: #92400e; padding: 3px 10px; border-radius: 4px; font-size: 12px;">{citations_str} citations</span>
    </td>
  </tr>

  <!-- Abstract -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <div style="border-left: 3px solid #6366f1; padding-left: 16px;">
        <p style="margin: 0; font-size: 15px; line-height: 1.7; color: #374151;">{abstract}</p>
      </div>
    </td>
  </tr>

  <!-- Link -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <a href="{url}" style="display: inline-block; background: #6366f1; color: #fff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-size: 14px; font-weight: 500;">Read Full Paper →</a>
    </td>
  </tr>

  <!-- Why -->
  <tr>
    <td style="padding: 0 40px 24px 40px;">
      <div style="background: #f9fafb; border-radius: 6px; padding: 16px;">
        <p style="margin: 0; font-size: 13px; color: #6b7280;">
          <strong>💡 Why this paper?</strong><br>
          {reason}
        </p>
      </div>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="padding: 20px 40px; border-top: 1px solid #e5e7eb;">
      <p style="margin: 0; font-size: 11px; color: #9ca3af;">📬 Delivered by PaperBot · Daily AI paper for students</p>
    </td>
  </tr>

</table>
</td>
</tr>
</table>
</body>
</html>"""
    return html


def send_email(html_body: str, subject: str) -> None:
    """Send an HTML email via SMTP. Config from environment variables."""
    smtp_server = os.environ["SMTP_SERVER"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ["SMTP_EMAIL"]
    password = os.environ["SMTP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"PaperBot <{sender}>"
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_mailer.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_mailer.py mailer.py
git commit -m "feat: add mailer module — HTML email builder + SMTP sender"
```

---

### Task 5: Main orchestrator

**Files:**
- Create: `main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `fetcher`, `scorer`, `mailer` modules
- Produces: `main() -> None` — entry point, called by `if __name__ == "__main__"`

- [ ] **Step 1: Write the failing test**

Create `tests/test_main.py`:

```python
import unittest
from unittest.mock import patch, MagicMock
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
        # Check subject line includes title and venue
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

        # Should not crash, should not send email
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
        # Subject should be truncated
        self.assertLess(len(subject), 150)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL (no module `main`)

- [ ] **Step 3: Write `main.py`**

```python
"""PaperBot: daily AI paper email delivery.

Fetches recent AI papers from arXiv and Semantic Scholar,
scores them for freshman-friendliness, and emails the best one.
"""
import sys
import fetcher
import scorer
import mailer


def main() -> None:
    """Fetch, score, and email the best paper of the day."""
    print("PaperBot: fetching papers...")
    papers = fetcher.fetch_all_papers()
    print(f"  Fetched {len(papers)} papers from arXiv + Semantic Scholar")

    if not papers:
        print("  No papers found. Exiting.")
        return

    print("PaperBot: scoring and ranking...")
    ranked = scorer.score_and_rank(papers, top_n=1)

    if not ranked:
        print("  No papers passed filters. Exiting.")
        return

    best = ranked[0]
    print(f"  Winner: {best['title'][:80]}... (score: {best['score']})")
    print(f"  Source: {best['source']} ({best['year']})")
    print(f"  Reason: {best['reason']}")

    # Build subject line
    title_short = best["title"]
    if len(title_short) > 80:
        title_short = title_short[:77] + "..."
    source_label = best.get("source", "Unknown")
    if best.get("year"):
        source_label += f" {best['year']}"
    subject = f"[Daily AI Paper] {title_short} — {source_label}"

    print("PaperBot: building email...")
    html = mailer.build_email(best)

    print("PaperBot: sending email...")
    try:
        mailer.send_email(html, subject)
        print("  Email sent successfully!")
    except Exception as e:
        print(f"  Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)

    print("PaperBot: done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_main.py main.py
git commit -m "feat: add main orchestrator — fetch → score → email pipeline"
```

---

### Task 6: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/daily.yml`

**Interfaces:**
- Consumes: the full project, environment variables set in GitHub Secrets
- Produces: automated daily run at 00:00 UTC (08:00 Beijing time)

- [ ] **Step 1: Write the workflow file**

Create `.github/workflows/daily.yml`:

```yaml
name: Daily AI Paper

on:
  schedule:
    # Run every day at 00:00 UTC (08:00 Beijing time)
    - cron: "0 0 * * *"
  workflow_dispatch:  # Allow manual trigger for testing

jobs:
  send-paper:
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run PaperBot
        env:
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_EMAIL: ${{ secrets.SMTP_EMAIL }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          RECIPIENT_EMAIL: ${{ secrets.RECIPIENT_EMAIL }}
        run: python main.py
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/daily.yml
git commit -m "feat: add GitHub Actions daily cron workflow"
```

---

### Task 7: End-to-end dry run & verification

**Files:**
- Modify: none (verification only)

**Interfaces:**
- Consumes: entire project
- Produces: confirmation that all modules work together

- [ ] **Step 1: Run all unit tests**

Run: `python -m pytest tests/ -v`
Expected: 17 tests PASS (4 fetcher + 7 scorer + 3 mailer + 3 main)

- [ ] **Step 2: Dry-run main.py (skip email, test API calls)**

Run:
```bash
python -c "
import fetcher
papers = fetcher.fetch_all_papers()
print(f'Fetched {len(papers)} papers')
for p in papers[:3]:
    print(f'  - {p[\"title\"][:60]} ({p[\"source\"]}, {p[\"year\"]})')

import scorer
ranked = scorer.score_and_rank(papers, top_n=3)
for p in ranked:
    print(f'  SCORE {p[\"score\"]}: {p[\"title\"][:60]} — {p[\"reason\"]}')
"
```
Expected: Output shows papers fetched and ranked. No crashes.

- [ ] **Step 3: Commit if anything changed**

```bash
git status
# Commit only if dry-run surfaced fixes
```

---

### Task 8: README and setup instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

Create `README.md`:

```markdown
# PaperBot — Daily AI Paper Email

自动每天推送一篇 Nature/顶刊 AI 论文到你的邮箱，专为 AI 大一学生设计。

## How It Works

每天早上 8:00（北京时间），GitHub Actions 自动运行脚本：

1. 从 arXiv + Semantic Scholar 抓取最新 AI 论文
2. 按"大一友好度"打分排序（综述/高引/顶会/新论文加分）
3. 将最佳论文格式化为邮件发送给你

## Setup

### 1. 准备 Gmail 应用密码

- 打开 [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords)
- 生成一个 "PaperBot" 应用密码，复制保存

### 2. Fork 这个仓库到你的 GitHub

### 3. 设置 GitHub Secrets

进入 Settings → Secrets and variables → Actions → New repository secret，添加：

| Secret | 值 |
|--------|-----|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_EMAIL` | `你的邮箱@gmail.com` |
| `SMTP_PASSWORD` | 刚才复制的应用密码 |
| `RECIPIENT_EMAIL` | `接收推送的邮箱` |

### 4. 测试

进入 Actions → Daily AI Paper → Run workflow → 手动触发，检查是否能收到邮件。

### 5. 完成

每天早上 8 点，查收邮件 📧

## 本地运行

```bash
cp .env.example .env
# 编辑 .env 填入真实值
pip install -r requirements.txt
python main.py
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```
