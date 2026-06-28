"""Scorer: rank papers by sophom*ore-friendliness and recency.

Scoring tuned for a second-year AI undergraduate — surveys are helpful
but primary research from top venues is weighted competitively.
"""
import random

TOP_VENUES = {
    "neurips", "icml", "iclr", "cvpr", "aaai", "acl", "emnlp",
    "nature", "science", "nature machine intelligence",
    "nature communications", "science advances",
    "ieee transactions on pattern analysis",
    "international conference on machine learning",
    "conference on neural information processing systems",
}

SURVEY_KEYWORDS = [
    "survey", "review", "tutorial", "overview",
    "a comprehensive", "state of the art", "benchmark",
]


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

    # Survey/review bonus — helpful for sophom*ores but not overwhelming
    if _is_survey(title):
        score += 2
        reasons.append("survey/review paper — great for building broad understanding")

    # Citation bonus
    if citations >= 5000:
        score += 3
        reasons.append("landmark paper — must-read in the field")
    elif citations > 100:
        score += 2
        reasons.append("well-cited paper")

    # Top venue bonus
    if _is_top_venue(source):
        score += 1
        reasons.append(f"from {source}")

    # Recency bonus — recent papers keep up with fast-moving AI
    if year >= 2024:
        score += 3
        reasons.append("cutting-edge recent work")
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
    kept = [p for p in papers if not _should_filter(p)]

    scored = []
    for p in kept:
        score, reasons = _score_paper(p)
        p = dict(p)
        p["score"] = round(score, 2)
        p["reason"] = reasons[0] if reasons else "AI paper you might find interesting"
        scored.append(p)

    scored.sort(key=lambda p: p["score"], reverse=True)
    return scored[:top_n]
