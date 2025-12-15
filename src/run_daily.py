from datetime import datetime
from pathlib import Path
import json
import re
from zoneinfo import ZoneInfo

from store import connect, upsert_articles, latest_articles
from market_moves import update_market_moves

from config import settings
from ingest import load_feeds, fetch_rss_items
from extract import now_iso
from prompt_builder import build_chatgpt_prompt
from emailer import send_email

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

URL_NOISE_PATTERNS = [
    "utm_source=",
    "utm_medium=",
    "utm_campaign=",
    "utm_term=",
    "utm_content=",
]


def is_noise_item(item: dict) -> bool:
    title = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "").strip()

    hay = " ".join([title, url, source]).lower()

    if POS_RE.search(hay):
        return False
    if NEG_RE.search(hay):
        return True
    return False


def clean_url(url: str) -> str:
    if not url:
        return url
    for pat in URL_NOISE_PATTERNS:
        if pat in url:
            return url.split("?", 1)[0]
    return url


def load_moves(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    s = settings()

    # ✅ Root del proyecto (…/workspace si src está en /workspace/src)
    project_root = Path(__file__).resolve().parent.parent

    conn = connect(s.db_path)

    # 1) Load feeds + fetch RSS items (ruta robusta)
    feeds_path = project_root / "feeds.yml"
    feeds = load_feeds(str(feeds_path))
    rss_items = fetch_rss_items(feeds, max_items=25)

    # 1.5) Anti-noise filter
    filtered = []
    for it in rss_items:
        it = dict(it)
        it["url"] = clean_url(it.get("url", ""))

        if not it.get("title") or not it.get("url"):
            continue
        if is_noise_item(it):
            continue

        filtered.append(it)

    # 2) DO NOT extract full text
    enriched = []
    fetched_at = now_iso()
    for it in filtered:
        enriched.append({**it, "text": None, "fetched_at": fetched_at})

    # 3) Store in SQLite
    upsert_articles(conn, enriched)

    # ✅ actualiza market moves del día (pero NO mates el run si falla)
    moves_path = project_root / "data" / "market_moves.json"
    try:
        update_market_moves(moves_path)
    except Exception as e:
        print(f"⚠️ market_moves falló (se continúa igual): {e}", flush=True)

    # 4.1) Load moves + as_of
    moves_doc = load_moves(moves_path)
    as_of = moves_doc.get("as_of") if isinstance(moves_doc, dict) else None
    if not as_of:
        as_of = datetime.utcnow().date().isoformat()

    # 5) Usar lo descargado HOY en este run; si viene vacío, fallback a BD pero SOLO HOY
    news_date = datetime.now(ZoneInfo("America/Bogota")).date().isoformat()

    candidates = latest_articles(conn, limit=s.max_articles * 5)
    today_only = [a for a in candidates if (a.get("published") or "")[:10] == news_date]

    articles = filtered if filtered else today_only[: s.max_articles]

    # 6) Dedupe + group + render digest
    deduped = dedupe_articles(articles, max_items=s.max_articles)
    grouped = group_articles(deduped)
    digest_md = digest_markdown(as_of=as_of, grouped=grouped, max_per_bucket=8)

    # 7) Build prompt
    prompt_txt = build_chatgpt_prompt(digest_md=digest_md, moves=moves_doc)

    # 7.5) Send email (cuerpo corto + adjuntos para evitar recortes/quoted text de Gmail)
    digest_bytes = digest_md.encode("utf-8")
    prompt_bytes = prompt_txt.encode("utf-8")

    # Ojo: cuerpo corto (Gmail no lo colapsa) + adjuntos con TODO el contenido
    body_short = f"""\
📌 PROMPT PARA CHATGPT (ver adjunto)

Instrucciones:
1) Abre el adjunto: prompt_for_chatgpt.txt
2) Copia y pega TODO en ChatGPT
3) (Opcional) Revisa latest_digest.txt para ver las noticias y links

Disclaimer: Contenido educativo/informativo, NO es asesoría financiera.

As of (Colombia): {as_of}
"""

    # ✅ Envío 1 a 1 (nadie ve a quién más se envió)
    recipients = [
        "eljj.personal@gmail.com",
        "alexandermanco@gmail.com",
    ]

    for r in recipients:
        send_email(
            subject=f"📈 Prompt de Mercados Colombia — {as_of}",
            body=body_short,
            to_emails=[r],
            attachments=[
                ("prompt_for_chatgpt.txt", prompt_bytes, "text/plain"),
                ("latest_digest.txt", digest_bytes, "text/plain"),
            ],
        )
        print(f"OK -> email enviado a {r}")

    # 8) Write outputs (ruta robusta)
    reports = project_root / "reports"
    reports.mkdir(exist_ok=True)

    (reports / "latest_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / "prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    (reports / f"{as_of}_digest.md").write_text(digest_md, encoding="utf-8")
    (reports / f"{as_of}_prompt_for_chatgpt.txt").write_text(prompt_txt, encoding="utf-8")

    print(f"Ítems RSS obtenidos: {len(rss_items)}")
    print(f"Después del filtro anti-ruido: {len(filtered)}")
    print("OK -> reports/latest_digest.md (digest generado)")
    print("OK -> reports/prompt_for_chatgpt.txt (prompt generado)")


if __name__ == "__main__":
    main()
