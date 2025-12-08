from datetime import datetime
import os

from config import settings
from store import connect, upsert_articles, latest_articles
from ingest import load_feeds, fetch_rss_items
from extract import extract_text_from_url, now_iso
from scoring import load_moves, score as score_fn, regime_from_score
from digest import dedupe_articles, group_articles, digest_markdown
from prompt_builder import build_chatgpt_prompt

def main():
    s = settings()
    conn = connect(s.db_path)

    feeds = load_feeds("feeds.yml")
    rss_items = fetch_rss_items(feeds, max_items=25)

    enriched = []
    for it in rss_items:
        # Optional: extract full text; comment out if you want faster runs
        text = extract_text_from_url(it["url"])
        enriched.append({
            **it,
            "text": text,
            "fetched_at": now_iso(),
        })

    inserted = upsert_articles(conn, enriched)

    moves_doc = load_moves("data/market_moves.json")
    as_of = moves_doc.get("as_of") or datetime.utcnow().date().isoformat()
    moves = moves_doc.get("moves", {})

    # Score is optional but useful as metadata in the digest
    score, _contrib = score_fn(moves)
    regime = regime_from_score(score)

    articles = latest_articles(conn, limit=s.max_articles)
    articles = dedupe_articles(articles, max_items=s.max_articles)
    grouped = group_articles(articles)

    digest_md = digest_markdown(as_of=as_of, grouped=grouped, max_per_bucket=8)

    # Add a small header with score/regime
    digest_md = (
        f"# Daily Global Markets Digest — {as_of}\n\n"
        f"**Quant score (optional):** `{score:.2f}`\n\n"
        f"**Regime (optional):** {regime}\n\n"
        + "\n".join(digest_md.splitlines()[3:])  # remove duplicate title from digest_markdown
    )

    prompt_txt = build_chatgpt_prompt(as_of=as_of, digest_md=digest_md, moves=moves)

    os.makedirs("reports", exist_ok=True)

    digest_path = f"reports/{as_of}_digest.md"
    prompt_path = f"reports/{as_of}_prompt_for_chatgpt.txt"

    with open(digest_path, "w", encoding="utf-8") as f:
        f.write(digest_md)

    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    # Convenience "latest" files
    with open("reports/latest_digest.md", "w", encoding="utf-8") as f:
        f.write(digest_md)

    with open("reports/prompt_for_chatgpt.txt", "w", encoding="utf-8") as f:
        f.write(prompt_txt)

    print(f"Inserted new articles: {inserted}")
    print(f"Score: {score:.2f} | Regime: {regime}")
    print(f"Wrote: {digest_path}")
    print(f"Wrote: {prompt_path}")
    print("Wrote: reports/latest_digest.md")
    print("Wrote: reports/prompt_for_chatgpt.txt")

if __name__ == "__main__":
    main()
