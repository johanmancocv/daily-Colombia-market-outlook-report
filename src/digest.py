from typing import List, Dict, Any
from collections import defaultdict
import re

# Map regions from feeds.yml to "buckets" shown in the report
REGION_ALIASES = {
    # Europe / UK
    "EU": "EU",
    "GB": "EU",
    "UK": "EU",

    # US
    "US": "US",
    "USA": "US",

    # LatAm
    "LATAM": "LATAM",

    # Colombia
    "CO": "CO",
    "COL": "CO",
    "COLOMBIA": "CO",

    # Asia
    "ASIA": "ASIA",
    "CN": "ASIA",
    "CHINA": "ASIA",
    "HK": "ASIA",
    "HONGKONG": "ASIA",
    "JP": "ASIA",
    "JAPAN": "ASIA",
    "KR": "ASIA",
    "KOREA": "ASIA",
    "TW": "ASIA",
    "TAIWAN": "ASIA",

    # Global catch-all
    "GLOBAL": "GLOBAL",
    "WORLD": "GLOBAL",
}

REGIONS_ORDER = ["ASIA", "EU", "US", "LATAM", "CO", "GLOBAL", "OTHER"]

# Labels shown in the digest (Spanish)
REGION_LABELS_ES = {
    "ASIA": "Asia",
    "EU": "Europa / Reino Unido",
    "US": "Estados Unidos",
    "LATAM": "Latinoamérica",
    "CO": "Colombia",
    "GLOBAL": "Global",
    "OTHER": "Otros",
}

TOPIC_LABELS_ES = {
    "markets": "Mercados",
    "macro": "Macro",
    "policy": "Política monetaria / Gobierno",
    "fx": "Divisas (FX)",
    "rates": "Tasas / Bonos",
    "commodities": "Materias primas",
    "stocks": "Acciones",
    "companies": "Empresas",
    "banks": "Bancos",
    "market_data": "Datos de mercado",
    "general": "General",
}


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9\s\-:/().]", "", s)
    return s


def _bucket_region(region: str) -> str:
    r = (region or "").strip().upper()
    r = re.sub(r"\s+", "", r)  # normalize "Hong Kong" -> "HONGKONG"
    return REGION_ALIASES.get(r, "OTHER")


def dedupe_articles(articles: List[Dict[str, Any]], max_items: int = 50) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for a in articles:
        key = _norm(a.get("title", "")) + "|" + (a.get("url", "") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= max_items:
            break
    return out


def group_articles(articles: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    returns {bucket_region: {topic: [articles...]}}
    where bucket_region is one of: ASIA, EU, US, LATAM, CO, GLOBAL, OTHER
    """
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for a in articles:
        raw_region = a.get("region", "") or ""
        region = _bucket_region(raw_region)

        topic = a.get("topic", "general") or "general"
        topic = (topic or "").strip().lower()

        grouped[region][topic].append(a)
    return grouped


def digest_markdown(
    as_of: str,
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]],
    max_per_bucket: int = 8
) -> str:
    md = []
    md.append(f"# Digest Diario de Mercados Globales — {as_of}")
    md.append("")
    md.append("_Generado automáticamente desde fuentes RSS. Proyecto educativo._")
    md.append("")

    # Regions in the order you want to see them
    for region in REGIONS_ORDER:
        if region not in grouped:
            continue

        md.append(f"## {REGION_LABELS_ES.get(region, region)}")
        topics = grouped[region]

        # Show topics in a sensible order if present
        preferred_topics = [
            "markets", "macro", "policy", "fx", "rates", "commodities",
            "stocks", "companies", "banks", "market_data", "general"
        ]
        topics_order = [t for t in preferred_topics if t in topics] + sorted(
            [t for t in topics.keys() if t not in preferred_topics]
        )

        for topic in topics_order:
            md.append(f"### {TOPIC_LABELS_ES.get(topic, topic)}")
            for a in topics[topic][:max_per_bucket]:
                title = (a.get("title") or "").strip()
                url = (a.get("url") or "").strip()
                source = (a.get("source") or "").strip()
                published = (a.get("published") or "").strip()
                pub_txt = f" — {published}" if published else ""

                md.append(f"- **{title}** ({source}){pub_txt}")
                if url:
                    md.append(f"  - {url}")
            md.append("")

        md.append("")
    return "\n".join(md)
