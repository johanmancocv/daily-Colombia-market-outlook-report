from datetime import datetime
from pathlib import Path
import json

from config import settings
from store import connect, upsert_articles, latest_articles
from ingest import load_feeds, fetch_rss_items
from extract import extract_text_from_url, now_iso
from prompt_builder import build_chatgpt_prompt


def render_digest_markdown(as_of: str, articles: list[dict], max_items: int = 35) -> str:
    lines = []
    lines.append(f"# Daily Global Markets Digest — {as_of}")
    lines.append("")
    lines.append("_Auto-generated from RSS sources. Educational project._")
    lines.append("")
    for a in articles[:max_items]:
        title = (a.get("title") or "").strip()
        url = (a.get("url") or "").strip()
        source = (a.get("source") or "").strip()
        region = (a.get("region") or "").strip()
        topic = (a.get("topic") or "").strip()
        published = (a.get("published") or "").strip()

        meta = " / ".join([x for x in [region, topic, source] if x])
        pub = f" — {published}" if published else ""
        lines.append(f"- **{title}** ({meta}){pub}")
        if url:
            lines.append(f"  - {url}")
    lines.append("")
    return "\n".join(lines)


def load_moves(path: str = "data/market_moves.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    s = settings()
    conn = connect(s.db_path)

    feeds = load_feeds("feeds.yml")
    rss_items = fetch_rss_items(feeds, max_items=25)

    enriched = []
    for it in rss_items:
        # Optional: extracting full text can be slow / blocked; keep or set text=None
        text = extract_text_from_url(it["url"])
        enriched.append({**it, "text": text, "fetched_at": now_iso()})

    upsert_articles(conn, enriched)

    moves_doc = load_moves("data/market_moves.json")
    as_of = moves_doc.get("as_of") if isinstance(moves_doc, dict) else None
    if not as_of:
        as_of = datetime.utcnow().date().isoformat()

    articles = latest_articles(conn, limit=s.max_articles)

    digest_md = render_digest_markdown(as_of=as_of, articles=articles, max_items=s.max_articles)
    prompt_txt = build_chatgpt_prompt(digest_md=digest_md, moves=moves_doc)

    reports = Path("reports")
    reports.mkdir(exist_ok=True)

    # latest
    (reports / "latest_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / "prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    # dated copies
    (reports / f"{as_of}_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / f"{as_of}_prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    print("OK -> reports/latest_digest.md")
    print("OK -> reports/prompt_for_chatgpt.txt")


if __name__ == "__main__":
    main()
