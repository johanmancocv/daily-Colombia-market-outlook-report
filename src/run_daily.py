from datetime import datetime
import os

from config import settings
from store import connect, upsert_articles, latest_articles, save_report
from ingest import load_feeds, fetch_rss_items
from extract import extract_text_from_url, now_iso
from scoring import load_moves, score as score_fn, regime_from_score
from llm import build_prompt, generate_structured_report
from render import to_markdown, pretty_json

def main():
    s = settings()
    conn = connect(s.db_path)

    feeds = load_feeds("feeds.yml")
    rss_items = fetch_rss_items(feeds, max_items=25)

    enriched = []
    for it in rss_items:
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

    score, contrib = score_fn(moves)
    regime = regime_from_score(score)

    articles = latest_articles(conn, limit=s.max_articles)

    prompt = build_prompt(
        as_of=as_of,
        score=score,
        regime=regime,
        contrib=contrib,
        articles=articles,
        moves=moves
    )

    report = generate_structured_report(model=s.openai_model, prompt=prompt)

    os.makedirs("reports", exist_ok=True)
    json_path = f"reports/{as_of}.json"
    md_path = f"reports/{as_of}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        f.write(pretty_json(report))

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(to_markdown(as_of, score, report))

    save_report(conn, as_of=as_of, model=s.openai_model, score=score, json_str=pretty_json(report), created_at=now_iso())

    print(f"Inserted new articles: {inserted}")
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")

if __name__ == "__main__":
    main()
