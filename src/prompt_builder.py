from datetime import date

def build_chatgpt_prompt(digest_md: str, moves: dict | None = None) -> str:
    moves = moves or {}
    as_of = moves.get("as_of", str(date.today()))
    m = moves.get("moves", {}) if isinstance(moves, dict) else {}

    def g(key, default="N/D"):
        return m.get(key, default)

    return f"""📌 COPIA Y PEGA ESTE PROMPT EN CHATGPT:

Actúa como analista de mercados (NO es asesoría financiera; es un proyecto educativo).

Regla crítica:
- Usa ÚNICAMENTE el “Digest de noticias” y los “Movimientos de mercado” provistos abajo.
- Si un dato no está, escribe “N/D” y NO lo inventes.
- Cuando afirmes algo, referencia al menos 1 link del digest (pegándolo).

Objetivo:
Producir un outlook para la bolsa colombiana (COLCAP) y sesgo para la sesión de hoy (antes de 8:30 AM Colombia).

Entrega EXACTAMENTE en este formato:

1) Régimen (risk-on / neutral / risk-off) y por qué (2-3 frases)
2) Top 5 drivers para Colombia (petróleo, USD/COP, tasas US, apetito EM, Europa/Asia) con impacto (+/–/mixto)
3) Sesgo 24h: bullish/neutral/bearish y Sesgo 1 semana: bullish/neutral/bearish
4) 3 escenarios (bull/base/bear) con probabilidad (que sume 1.0), catalizadores e invalidación
5) “Qué vigilar hoy”: 5 bullets (eventos, datos, headlines a monitorear)
6) Fuentes usadas: lista de 5–10 URLs del digest (sin inventar)
7) Limitaciones (1 párrafo)

Movimientos de mercado (as_of={as_of}):
- Brent: {g("BRENT_pct")}%
- USD/COP: {g("USD_COP_pct")}%
- US10Y: {g("US10Y_bp")} bp
- DXY: {g("DXY_pct")}%
- VIX: {g("VIX_pct")}%
- EEM: {g("EEM_pct")}%

Digest de noticias (con links):
{digest_md}
"""
