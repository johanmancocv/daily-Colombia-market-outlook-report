from datetime import datetime
from pathlib import Path
import json
import re

from config import settings
from store import connect, upsert_articles, latest_articles
from ingest import load_feeds, fetch_rss_items
from extract import now_iso
from prompt_builder import build_chatgpt_prompt

from digest import dedupe_articles, group_articles, digest_markdown


# --- Anti-noise filter rules (title/url/source based) ---
NEGATIVE_PATTERNS = [
    r"\b(celebrity|celeb|hollywood|movie|film|serie|netflix|music|album|grammy|oscar)\b",
    r"\b(fashion|beauty|lifestyle|travel|recipe|food|cooking|horoscope|astrology)\b",
    r"\b(sports?|soccer|football|nba|nfl|mlb|nhl|fifa|ufc|boxing|tennis|golf)\b",
    r"\b(crime|murder|killed|shooting|robbery|kidnap|drug)\b",
    r"\b(weather|storm|hurricane|earthquake)\b",
    r"\b(opinion|column|editorial|podcast)\b",
]

# If any of these appear, we KEEP even if it contains some generic words
POSITIVE_PATTERNS = [
    r"\b(stocks?|equities|shares?|bonds?|yields?|treasur(?:y|ies)|credit|spreads?)\b",
    r"\b(markets?|futures?|index|indices|nasdaq|s&p|dow|nikkei|hang seng|kospi|taiex)\b",
    r"\b(fed|fomc|powell|ecb|boj|pboc|banrep|banco de la rep(?:u|ú)blica)\b",
    r"\b(inflation|cpi|ppi|jobs report|payrolls|unemployment|gdp|pmi)\b",
    r"\b(usd/cop|trm|dollar|dólar|fx|forex|currency|peso|yuan|yen|won)\b",
    r"\b(oil|brent|wti|gas|energy|commodit(?:y|ies))\b",
    r"\b(ecopetrol|bancolombia|grupo aval|davivienda|grupo sura|argos|nutresa|isa)\b",
    r"\b(risk[- ]on|risk[- ]off|vix|dxy|emerging markets|eem)\b",
]

NEG_RE = re.compile("|".join(NEGATIVE_PATTERNS), re.IGNORECASE)
POS_RE = re.compile("|".join(POSITIVE_PATTERNS), re.IGNORECASE)

# Optional: drop obvious duplicates/trackers in URLs
URL_NOISE_PATTERNS = [
    r"utm_source=",
    r"utm_medium=",
    r"utm_campaign=",
]


def is_noise_item(item: dict) -> bool:
    title = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "").strip()

    hay = " ".join([title, url, source]).lower()

    # Keep if clearly relevant (positive match)
    if POS_RE.search(hay):
        return False

    # Drop if clearly noise (negative match)
    if NEG_RE.search(hay):
        return True

    # If neither positive nor negative matched:
    # Keep by default (conservative), OR be stricter:
    # return True  # <- stricter mode
    return False


def clean_url(url: str) -> str:
    if not url:
        return url
    # quick cleanup: remove common utm parameters (optional)
    # (simple approach; not perfect but fine)
    for pat in URL_NOISE_PATTERNS:
        if pat in url:
            # If URL has ?, strip query entirely
            return url.split("?", 1)[0]
    return url


def load_moves(path: str = "data/market_moves.json") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    s = settings()
    conn = connect(s.db_path)

    # 1) Load feeds + fetch RSS items
    feeds = load_feeds("feeds.yml")
    rss_items = fetch_rss_items(feeds, max_items=25)

    # 1.5) Anti-noise filter (title/url/source based)
    filtered = []
    for it in rss_items:
        it = dict(it)
        it["url"] = clean_url(it.get("url", ""))
        if not it.get("title") or not it.get("url"):
            continue
        if is_noise_item(it):
            continue
        filtered.append(it)

    # 2) DO NOT extract full text (faster + less blocking)
    enriched = []
    fetched_at = now_iso()
    for it in filtered:
        enriched.append({**it, "text": None, "fetched_at": fetched_at})

    # 3) Store in SQLite
    upsert_articles(conn, enriched)

    # 4) Figure out "as_of"
    moves_doc = load_moves("data/market_moves.json")
    as_of = moves_doc.get("as_of") if isinstance(moves_doc, dict) else None
    if not as_of:
        as_of = datetime.utcnow().date().isoformat()

    # 5) Pull latest articles (already stored)
    articles = latest_articles(conn, limit=s.max_articles)

    # 6) Dedupe + group + render digest
    deduped = dedupe_articles(articles, max_items=s.max_articles)
    grouped = group_articles(deduped)
    digest_md = digest_markdown(as_of=as_of, grouped=grouped, max_per_bucket=8)

    # 7) Build the prompt for ChatGPT copy/paste
    prompt_txt = build_chatgpt_prompt(digest_md=digest_md, moves=moves_doc)

    # 8) Write outputs
    reports = Path("reports")
    reports.mkdir(exist_ok=True)

    (reports / "latest_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / "prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    (reports / f"{as_of}_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / f"{as_of}_prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    print(f"Fetched RSS items: {len(rss_items)}")
    print(f"After noise filter: {len(filtered)}")
    print("OK -> reports/latest_digest.md")
    print("OK -> reports/prompt_for_chatgpt.txt")


if __name__ == "__main__":
    main()
