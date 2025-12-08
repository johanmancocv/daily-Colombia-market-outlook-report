from typing import Dict, Any

def build_chatgpt_prompt(as_of: str, digest_md: str, moves: Dict[str, float]) -> str:
    # moves keys expected: BRENT_pct, USD_COP_pct, US10Y_bp, DXY_pct, VIX_pct, EEM_pct, COLCAP_pct (optional)
    def fmt_pct(x):
        try:
            return f"{float(x):+.2f}%"
        except Exception:
            return "N/A"

    def fmt_bp(x):
        try:
            return f"{float(x):+.1f} bp"
        except Exception:
            return "N/A"

    lines = []
    lines.append("Debes copiar y pegar esto en Chat GPT: ")
   lines.append("Actúa como analista de mercados (NO asesoría financiera; es un proyecto educativo).")
    lines.append("Usa ÚNICAMENTE el “Digest de noticias” y los “Movimientos de mercado” que pego abajo.")
    lines.append("")
    lines.append("Objetivo: producir un outlook para la bolsa colombiana (COLCAP) y sesgo para la sesión de hoy (antes de 8:30 AM Colombia).")
    lines.append("")
    lines.append("Entrega en este formato:")
    lines.append("1) Régimen (risk-on / neutral / risk-off) y por qué (2-3 frases)")
    lines.append("2) Top 5 drivers para Colombia (petróleo, USD/COP, tasas US, apetito EM, Europa/Asia) con impacto (+/–/mixto)")
    lines.append("3) Sesgo 24h: bullish/neutral/bearish y Sesgo 1 semana: bullish/neutral/bearish")
    lines.append("4) 3 escenarios (bull/base/bear) con probabilidad (que sume 1.0), catalizadores e invalidación")
    lines.append("5) “Qué vigilar hoy”: 5 bullets (eventos, datos, headlines a monitorear)")
    lines.append("6) Limitaciones (1 párrafo)")
    lines.append("")
    lines.append("IMPORTANTE:")
    lines.append("- Si falta data, dilo explícitamente y no inventes números.")
    lines.append("- Cita evidencia: cuando menciones un headline, referencia el link del digest (puedes copiar el URL).")
    lines.append("")
    lines.append("Movimientos de mercado (si están disponibles):")
    lines.append(f"- COLCAP: {fmt_pct(moves.get('COLCAP_pct'))}")
    lines.append(f"- Brent: {fmt_pct(moves.get('BRENT_pct'))}")
    lines.append(f"- USD/COP: {fmt_pct(moves.get('USD_COP_pct'))}")
    lines.append(f"- US10Y: {fmt_bp(moves.get('US10Y_bp'))}")
    lines.append(f"- DXY: {fmt_pct(moves.get('DXY_pct'))}")
    lines.append(f"- VIX: {fmt_pct(moves.get('VIX_pct'))}")
    lines.append(f"- EEM: {fmt_pct(moves.get('EEM_pct'))}")
    lines.append("")
    lines.append("Digest de noticias (con links):")
    lines.append(digest_md.strip())
    lines.append("")
    return "\n".join(lines)
