from typing import Dict, Any
import json

def to_markdown(as_of: str, score: float, report: Dict[str, Any]) -> str:
    md = []
    md.append(f"# Colombia Market Nowcast — {as_of}")
    md.append("")
    md.append(f"**Quant score:** `{score:.2f}`")
    md.append(f"**Regime:** {report['regime']}")
    md.append(f"**Bias (24h / 1w):** {report['bias_24h']} / {report['bias_1w']}")
    md.append("")
    md.append("## Top drivers")
    for d in report["top_drivers"]:
        md.append(f"- **{d['driver']}** ({d['impact']}): {d['why']}")
        if d["citations"]:
            md.append(f"  - Sources: " + " | ".join(d["citations"]))
    md.append("")
    md.append("## Scenarios")
    for s in report["scenarios"]:
        md.append(f"### {s['name'].upper()} — p={s['probability']:.2f}")
        md.append(s["narrative"])
        md.append(f"**Invalidated by:** {s['invalidated_by']}")
        if s["citations"]:
            md.append("**Sources:** " + " | ".join(s["citations"]))
        md.append("")
    md.append("## Watch next")
    for w in report["watch_next"]:
        md.append(f"- {w}")
    md.append("")
    md.append("## Limitations")
    md.append(report["limitations"])
    md.append("")
    md.append("---")
    md.append("_Educational/research project only. Not financial advice._")
    return "\n".join(md)

def pretty_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
