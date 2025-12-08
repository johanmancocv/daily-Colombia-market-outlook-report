from typing import List, Dict, Any
from collections import defaultdict
import re

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9\s\-:/().]", "", s)
    return s

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
    # returns {region: {topic: [articles...]}}
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for a in articles:
        region = a.get("region", "OTHER") or "OTHER"
        topic = a.get("topic", "general") or "general"
        grouped[region][topic].append(a)
    return grouped

def digest_markdown(as_of: str, grouped: Dict[str, Dict[str, List[Dict[str, Any]]]], max_per_bucket: int = 8) -> str:
    md = []
    md.append(f"# Daily Global Markets Digest — {as_of}")
    md.append("")
    md.append("_Auto-generated from RSS/scraped sources. Educational project._")
    md.append("")

    regions_order = ["ASIA", "EU", "US", "LATAM", "CO", "OTHER"]
    for region in regions_order:
        if region not in grouped:
            continue
        md.append(f"## {region}")
        topics = grouped[region]
        for topic in sorted(topics.keys()):
            md.append(f"### {topic}")
            for a in topics[topic][:max_per_bucket]:
                title = a.get("title", "").strip()
                url = a.get("url", "").strip()
                source = a.get("source", "").strip()
                published = (a.get("published") or "").strip()
                pub_txt = f" — {published}" if published else ""
                md.append(f"- **{title}** ({source}){pub_txt}")
                if url:
                    md.append(f"  - {url}")
            md.append("")
        md.append("")
    return "\n".join(md)
