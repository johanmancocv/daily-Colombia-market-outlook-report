from typing import List, Dict, Any
import yaml
import feedparser

def load_feeds(path: str = "feeds.yml") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["feeds"]

def fetch_rss_items(feeds: List[Dict[str, Any]], max_items: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries[:max_items]:
            url = e.get("link")
            title = (e.get("title") or "").strip()
            published = e.get("published") or e.get("updated")
            if not url or not title:
                continue
            items.append({
                "url": url,
                "title": title,
                "published": published,
                "source": feed["name"],
                "region": feed["region"],
                "topic": feed["topic"],
            })
    return items
