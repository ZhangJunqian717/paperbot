"""PaperBot: daily AI paper email delivery.

Fetches recent AI papers from arXiv and Semantic Scholar,
scores them for sophomore-friendliness, and emails the best one.
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
