from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
TZ_CO = ZoneInfo("America/Bogota")

# Símbolos Yahoo
TICKERS = {
    "BRENT": "BZ=F",
    "USD_COP": "USDCOP=X",
    "US10Y": "^TNX",        # Nota: ^TNX = yield*10 (ej: 44.50 => 4.45%)
    "DXY": "DX-Y.NYB",
    "VIX": "^VIX",
    "EEM": "EEM",
}

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


def _pct_change(price: float | None, prev: float | None) -> float | None:
    if price is None or prev is None or prev == 0:
        return None
    return (price / prev - 1.0) * 100.0


def _fetch_quotes(symbols: list[str]) -> dict[str, dict]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyOutlookBot/1.0)"}
    with httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True, headers=headers) as client:
        r = client.get(YAHOO_QUOTE_URL, params={"symbols": ",".join(symbols)})
        r.raise_for_status()
        data = r.json()

    results = (data.get("quoteResponse") or {}).get("result") or []
    return {q.get("symbol"): q for q in results if q.get("symbol")}


def update_market_moves(out_path: str | Path = "data/market_moves.json") -> dict:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    symbols = list(TICKERS.values())
    quotes = _fetch_quotes(symbols)

    def get(sym: str) -> tuple[float | None, float | None]:
        q = quotes.get(sym, {}) or {}
        return q.get("regularMarketPrice"), q.get("regularMarketPreviousClose")

    moves: dict[str, object] = {}

    # Brent %
    brent_p, brent_prev = get(TICKERS["BRENT"])
    brent_pct = _pct_change(brent_p, brent_prev)
    moves["BRENT_pct"] = round(brent_pct, 2) if brent_pct is not None else "N/D"

    # USD/COP %
    fx_p, fx_prev = get(TICKERS["USD_COP"])
    fx_pct = _pct_change(fx_p, fx_prev)
    moves["USD_COP_pct"] = round(fx_pct, 2) if fx_pct is not None else "N/D"

    # US10Y bp (usar ^TNX: yield*10)
    tnx_p, tnx_prev = get(TICKERS["US10Y"])
    if tnx_p is not None and tnx_prev is not None:
        # Diferencia en puntos base: (tnx_p - tnx_prev) * 10
        # Ej: 44.50 -> 4.45% ; delta 0.20 => 0.02% => 2 bp
        moves["US10Y_bp"] = round((tnx_p - tnx_prev) * 10.0, 1)
    else:
        moves["US10Y_bp"] = "N/D"

    # DXY %
    dxy_p, dxy_prev = get(TICKERS["DXY"])
    dxy_pct = _pct_change(dxy_p, dxy_prev)
    moves["DXY_pct"] = round(dxy_pct, 2) if dxy_pct is not None else "N/D"

    # VIX %
    vix_p, vix_prev = get(TICKERS["VIX"])
    vix_pct = _pct_change(vix_p, vix_prev)
    moves["VIX_pct"] = round(vix_pct, 2) if vix_pct is not None else "N/D"

    # EEM %
    eem_p, eem_prev = get(TICKERS["EEM"])
    eem_pct = _pct_change(eem_p, eem_prev)
    moves["EEM_pct"] = round(eem_pct, 2) if eem_pct is not None else "N/D"

    doc = {
        "as_of": datetime.now(TZ_CO).date().isoformat(),
        "moves": moves,
        "source": "Yahoo Finance quote (regularMarketPrice vs regularMarketPreviousClose)",
    }

    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
