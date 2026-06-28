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
            arxiv_url = arxiv_id.replace("http://", "https://")
            # Remove version suffix (v1, v2, etc.)
            arxiv_url = re.sub(r"v\d+$", "", arxiv_url)

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

        source = venue if venue else "Unknown"

        paper_url = item.get("url", "")
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
