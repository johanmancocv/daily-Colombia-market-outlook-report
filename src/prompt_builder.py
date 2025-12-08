from datetime import date


def build_chatgpt_prompt(digest_md: str, moves: dict | None = None) -> str:
    moves = moves or {}
    as_of = moves.get("as_of", str(date.today()))

    def fmt_pct(pct: float | None, level: float | None, level_label: str | None = None) -> str:
        if pct is not None:
            return f"{pct:.2f}%"
        if level is not None:
            if level_label:
                return f"N/D (nivel: {level:,.2f} {level_label})"
            return f"N/D (nivel: {level:,.2f})"
        return "N/D"

    def fmt_bp(bp: float | None) -> str:
        return "N/D" if bp is None else f"{bp:.1f} bp"

    brent_txt = fmt_pct(moves.get("brent"), moves.get("brent_level"), "USD")
    usdcop_txt = fmt_pct(moves.get("usdcop"), moves.get("usdcop_level"), "COP")
    dxy_txt = fmt_pct(moves.get("dxy"), moves.get("dxy_level"))
    vix_txt = fmt_pct(moves.get("vix"), moves.get("vix_level"))
    eem_txt = fmt_pct(moves.get("eem"), moves.get("eem_level"), "USD")
    us10y_txt = fmt_bp(moves.get("us10y_bp"))

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
- Brent: {brent_txt}
- USD/COP: {usdcop_txt}
- US10Y: {us10y_txt}
- DXY: {dxy_txt}
- VIX: {vix_txt}
- EEM: {eem_txt}

Digest de noticias (con links):
{digest_md}
"""
