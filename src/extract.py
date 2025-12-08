from typing import Optional
import httpx
import trafilatura
from datetime import datetime, timezone
import time
import random

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
    html = fetch_html(url)
    if not html:
        return None
    downloaded = trafilatura.extract(html, include_comments=False, include_tables=False)
    if not downloaded:
        return None
    # keep it bounded
    return downloaded.strip()[:12000]
