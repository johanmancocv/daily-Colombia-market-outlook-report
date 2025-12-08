from typing import List, Dict, Any
import yaml
import feedparser
import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


def load_feeds(path: str = "feeds.yml") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("feeds", [])


def _parse_feed(url: str) -> Any:
    """
    Descarga el RSS con timeout real (evita que se quede colgado) y luego lo parsea con feedparser.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyOutlookBot/1.0)"}
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        r.raise_for_status()
        return feedparser.parse(r.text)


def fetch_rss_items(feeds: List[Dict[str, Any]], max_items: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for i, feed in enumerate(feeds, start=1):
        name = feed.get("name", "Unknown")
        url = feed.get("url", "")
        if not url:
            continue

        print(f"🔎 [{i}/{len(feeds)}] RSS: {name} -> {url}", flush=True)

        try:
            parsed = _parse_feed(url)
        except Exception as ex:
            print(f"⚠️ RSS error: {name} -> {url} :: {ex}", flush=True)
            continue

        status = getattr(parsed, "status", None)
        if status is not None:
            try:
                if int(status) >= 400:
                    print(f"⚠️ RSS falló HTTP {status}: {name} -> {url}", flush=True)
                    continue
            except Exception:
                pass

        bozo = getattr(parsed, "bozo", 0)
        if bozo:
            err = getattr(parsed, "bozo_exception", None)
            if err:
                print(f"⚠️ RSS parse warning: {name} -> {err}", flush=True)

        for e in getattr(parsed, "entries", [])[:max_items]:
            entry_url = e.get("link")
            title = (e.get("title") or "").strip()
            published = e.get("published") or e.get("updated")
            if not entry_url or not title:
                continue

            items.append(
                {
                    "url": entry_url,
                    "title": title,
                    "published": published,
                    "source": feed.get("name", ""),
                    "region": feed.get("region", ""),
                    "topic": feed.get("topic", ""),
                }
            )

    return items
