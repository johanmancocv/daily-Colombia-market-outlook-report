
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import csv
import io
import json

import httpx

TZ_CO = ZoneInfo("America/Bogota")
UTC = ZoneInfo("UTC")

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyOutlookBot/1.0)"}

# Stooq symbols (no auth)
# Brent (ICE Brent futures): cb.f
# DXY (US Dollar Index): usd_i
# VIX (VIX futures proxy): vi.f
# EEM (ETF): eem.us
STOOQ_MAP = {
    "brent": "cb.f",
    "dxy": "usd_i",
    "vix": "vi.f",
    "eem": "eem.us",
    # Intento USD/COP en Stooq (si no funciona cae a ER API)
    "usdcop": "usdcop",
}

FRED_DGS10_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
ER_API_USD = "https://open.er-api.com/v6/latest/USD"


def _safe_float(x: str | None) -> float | None:
    if x is None:
        return None
    x = str(x).strip()
    if not x or x.upper() in {"N/A", "NA", "NULL", "."}:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _stooq_last_two_closes(symbol: str) -> tuple[float | None, float | None]:
    """
    Returns (last_close, prev_close) using Stooq CSV.
    """
    url = "https://stooq.com/q/l/"
    params = {"s": symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}

    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(url, params=params)
        r.raise_for_status()

    text = r.text.strip()
    if not text:
        return (None, None)

    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    if not rows:
        return (None, None)

    # Stooq usually returns ascending; we take last two rows
    last = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else None

    last_close = _safe_float(last.get("Close"))
    prev_close = _safe_float(prev.get("Close")) if prev else None

    return (last_close, prev_close)


def _pct_change(last: float | None, prev: float | None) -> float | None:
    if last is None or prev is None or prev == 0:
        return None
    return (last / prev - 1.0) * 100.0


def _fetch_usdcop_fallback() -> float | None:
    """
    Fallback USD->COP using open.er-api.com
    """
    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(ER_API_USD)
        r.raise_for_status()
        data = r.json()

    # typical payload: {"rates": {"COP": 4xxx, ...}}
    rates = data.get("rates") if isinstance(data, dict) else None
    if not isinstance(rates, dict):
        return None
    cop = rates.get("COP")
    return _safe_float(cop)


def _fetch_us10y_bp_change() -> float | None:
    """
    Uses FRED DGS10 CSV (no key). Returns daily change in basis points.
    """
    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(FRED_DGS10_CSV)
        r.raise_for_status()

    lines = r.text.strip().splitlines()
    if len(lines) < 3:
        return None

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    vals: list[float] = []
    for row in reader:
        v = _safe_float(row.get("DGS10"))
        if v is not None:
            vals.append(v)

    if len(vals) < 2:
        return None

    last = vals[-1]
    prev = vals[-2]
    # DGS10 is in %, convert to bp change
    return (last - prev) * 100.0


def update_market_moves(out_path: Path) -> dict:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Stooq-based pct moves
    moves: dict[str, float | None] = {}
    for key, sym in STOOQ_MAP.items():
        try:
            last, prev = _stooq_last_two_closes(sym)
            moves[key] = _pct_change(last, prev)
        except Exception:
            moves[key] = None

    # 2) USD/COP fallback if stooq failed
    if moves.get("usdcop") is None:
        try:
            # Here we can't compute % change without yesterday; best effort:
            # try stooq again but if no prev, keep None
            usd_cop = _fetch_usdcop_fallback()
            # Without previous close, we leave pct as None (better than inventing).
            # If you later want % change, we can store level too.
            if usd_cop is not None:
                # store level in a separate field
                pass
        except Exception:
            pass

    # 3) US10Y (bp)
    try:
        us10y_bp = _fetch_us10y_bp_change()
    except Exception:
        us10y_bp = None

    as_of = datetime.now(TZ_CO).date().isoformat()

    doc = {
        "as_of": as_of,
        # percent moves (None => your prompt should show N/D ideally)
        "brent": moves.get("brent"),
        "usdcop": moves.get("usdcop"),
        "dxy": moves.get("dxy"),
        "vix": moves.get("vix"),
        "eem": moves.get("eem"),
        # basis points move
        "us10y_bp": us10y_bp,
        # helpful metadata
        "source": "stooq+fred",
        "generated_at": datetime.now(TZ_CO).isoformat(),
    }

    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
