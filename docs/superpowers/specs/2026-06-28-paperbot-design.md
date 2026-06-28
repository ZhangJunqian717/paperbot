# PaperBot — Daily AI Paper Email Delivery

**Goal:** Automatically fetch, filter, and email one AI paper daily from
top-tier journals and conferences, tailored for a freshman AI student.

**Status:** Design approved 2026-06-28

---

## User Experience

Every morning at 8:00 Beijing time, the user receives an HTML email:

- **Subject:** `[Daily AI Paper] <Paper Title> — <Venue Year>`
- **Body:** Paper title, source venue, citation count, relevance tags,
  full English abstract, arXiv link, and a one-line "why this paper?"
  explanation.

The email is designed to be readable in 2 minutes — scan, save, or skip.

## Components

### 1. Fetcher (`fetcher.py`)

Queries two free APIs:

| API | Purpose | Rate Limit |
|-----|---------|------------|
| arXiv API | Recent AI papers (cs.AI, cs.LG, cs.CL, cs.CV) | 1 req / 3 sec |
| Semantic Scholar | Citation counts, venue info, Nature/Science papers | 100 req / 5 min |

### 2. Scorer (`scorer.py`)

Each paper gets a composite score. Highest score wins the daily pick.

| Criterion | Points |
|-----------|--------|
| Title matches survey/review/tutorial (case-insensitive) | +3 |
| Citation count > 100 | +2 |
| Venue is top conference (NeurIPS, ICML, ICLR, CVPR, AAAI, ACL, EMNLP) | +1 |
| Venue is Nature/Science family | +1 |
| Year 2024–2026 | +3 |
| Year 2022–2023 | +1 |
| Year ≤ 2021 (non-landmark, < 5000 citations) | filtered out |
| Random jitter (±0.5) | prevents same paper every day |

### 3. Mailer (`mailer.py`)

Sends HTML email via SMTP (Gmail by default).

- Config via environment variables:
  - `SMTP_SERVER` (default: smtp.gmail.com)
  - `SMTP_PORT` (default: 587)
  - `SMTP_EMAIL` — sender address
  - `SMTP_PASSWORD` — app password
  - `RECIPIENT_EMAIL` — your receiving address

### 4. Orchestrator (`main.py`)

```python
import fetcher, scorer, mailer

papers = fetcher.fetch_papers(query="artificial intelligence", max_results=50)
ranked = scorer.score_and_rank(papers, top_n=1)
best = ranked[0]
html = mailer.build_email(best)
mailer.send(html)
```

## Scheduling

GitHub Actions workflow: `.github/workflows/daily.yml`

- Cron: `0 0 * * *` (UTC midnight ≈ Beijing 8:00 AM)
- Runs `python main.py`
- Secrets stored in GitHub repository settings

## Tech Stack

- Python 3.13
- `requests` (HTTP client)
- `smtplib`, `email` (stdlib, email)
- GitHub Actions (cron scheduler)

## File Tree

```
.
├── main.py
├── fetcher.py
├── scorer.py
├── mailer.py
├── requirements.txt
├── .github/
│   └── workflows/
│       └── daily.yml
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-06-28-paperbot-design.md
        └── plans/
            └── 2026-06-28-paperbot-plan.md
```

## Constraints

- No paid APIs — only free tier services
- No database — stateless, fetch → score → send
- Paper year ≥ 2022 unless landmark (> 5000 citations)
- All paper content in English (original language)
- Single paper per day, one email
