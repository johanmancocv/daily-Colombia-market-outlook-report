
from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from time import mktime

import yaml
import feedparser
import httpx
from dateutil import parser as dtparser

TZ_CO = ZoneInfo("America/Bogota")
UTC = ZoneInfo("UTC")

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyOutlookBot/1.0)"}

LAST_HOURS = 24  # ✅ últimas 24h

def load_feeds(path: str = "feeds.yml") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("feeds", [])

def _parse_dt_text(text: str) -> datetime | None:
    if not text:
        return None
    try:
        dt = dtparser.parse(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(TZ_CO)
    except Exception:
        return None

def _entry_dt(entry: dict) -> datetime | None:
    # 1) Try string fields
    for k in ("published", "updated", "created"):
        v = entry.get(k)
        if v:
            dt = _parse_dt_text(v)
            if dt:
                return dt

    # 2) Try feedparser struct_time fields
    for k in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(k)
        if t:
            try:
                return datetime.fromtimestamp(mktime(t), tz=UTC).astimezone(TZ_CO)
            except Exception:
                pass

    return None

def _parse_feed(url: str) -> Any:
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
        r = client.get(url)
        r.raise_for_status()
        return feedparser.parse(r.text)

def fetch_rss_items(feeds: List[Dict[str, Any]], max_items: int = 50) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    now = datetime.now(TZ_CO)
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)  # ✅ solo HOY

    for i, feed in enumerate(feeds, start=1):
        name = feed.get("name", "Unknown")
        url = feed.get("url", "")
        if not url:
            continue

        print(f"🔎 [{i}/{len(feeds)}] RSS: {name}", flush=True)

        try:
            parsed = _parse_feed(url)
        except Exception as ex:
            print(f"⚠️ RSS error: {name} -> {url} :: {ex}", flush=True)
            continue

        for e in getattr(parsed, "entries", [])[:max_items]:
            entry_url = e.get("link")
            title = (e.get("title") or "").strip()

            if not entry_url or not title:
                continue

            pub_dt = _entry_dt(e)

            # ✅ Regla: solo últimas 24h
            if pub_dt is None or pub_dt < cutoff:
                continue

            items.append(
                {
                    "url": entry_url,
                    "title": title,
                    "published": pub_dt.isoformat(),
                    "source": feed.get("name", ""),
                    "region": feed.get("region", ""),
                    "topic": feed.get("topic", ""),
                }
            )

    return items

