import json
from typing import Dict, Any, Tuple

# Simple, explainable "Colombia pressure score" in [-10, +10]
# Positive => supportive for COL equities; Negative => headwinds.
WEIGHTS = {
    "BRENT_pct":  2.0,   # oil up supports Colombia
    "USD_COP_pct": -2.0, # USD/COP up = COP weaker = usually risk-off for local equities
    "US10Y_bp":  -0.15,  # yields up (bp) is negative for EM (scale down)
    "DXY_pct":   -1.0,
    "VIX_pct":   -1.5,
    "EEM_pct":    1.0
}

def load_moves(path: str = "data/market_moves.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def score(moves: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    contrib = {}
    s = 0.0
    for k, w in WEIGHTS.items():
        v = float(moves.get(k, 0.0))
        c = w * v
        contrib[k] = c
        s += c
    # clamp
    s = max(-10.0, min(10.0, s))
    return s, contrib

def regime_from_score(s: float) -> str:
    if s >= 3.5:
        return "risk-on (supportive)"
    if s <= -3.5:
        return "risk-off (headwinds)"
    return "neutral / mixed"
