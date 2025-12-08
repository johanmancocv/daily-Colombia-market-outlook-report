from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone
import time
import random

import httpx

DEFAULT_HEADERS = {
    "User-Agent": "market-nowcast-co/1.0 (+research-project; respectful-rate-limit)"
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_html(url: str, timeout_s: float = 20.0) -> Optional[str]:
    # polite jitter so you don’t hammer sites
    time.sleep(0.2 + random.random() * 0.4)

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout_s) as client:
        r = client.get(url)
        if r.status_code >= 400:
            return None
        return r.text


def extract_text_from_url(url: str) -> Optional[str]:
    # ✅ Import lazy: no rompe el proyecto si trafilatura no está instalada
    try:
        import trafilatura  # type: ignore
    except ModuleNotFoundError:
        return None

    html = fetch_html(url)
    if not html:
        return None

    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    if not extracted:
        return None

    # keep it bounded
    return extracted.strip()[:12000]
