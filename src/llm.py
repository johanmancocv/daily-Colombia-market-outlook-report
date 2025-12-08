import json
from typing import Any, Dict, List
from openai import OpenAI

def build_prompt(as_of: str, score: float, regime: str, contrib: Dict[str, float],
                 articles: List[Dict[str, Any]], moves: Dict[str, float]) -> str:
    # Keep the LLM grounded with explicit inputs + URLs.
    # You can tighten/expand this as you iterate.
    lines = []
    lines.append(f"As-of date: {as_of}")
    lines.append(f"Quant score: {score:.2f} (regime: {regime})")
    lines.append(f"Contributions: {json.dumps(contrib, ensure_ascii=False)}")
    lines.append(f"Market moves: {json.dumps(moves, ensure_ascii=False)}")
    lines.append("\nArticles (most recent first):")
    for a in articles[:35]:
        lines.append(f"- [{a['source']}] ({a.get('region')}/{a.get('topic')}) {a['title']} | {a['url']}")
    lines.append("\nTask: Produce a Colombia (COLCAP) outlook based ONLY on the inputs above.")
    lines.append("Rules:")
    lines.append("- Not financial advice. Educational/research only.")
    lines.append("- Be explicit about uncertainty; use scenarios.")
    lines.append("- Cite evidence by referencing the article URLs in `citations` fields.")
    return "\n".join(lines)

def generate_structured_report(model: str, prompt: str) -> Dict[str, Any]:
    client = OpenAI()

    schema = {
        "name": "colombia_market_nowcast",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "regime": {"type": "string"},
                "bias_24h": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
                "bias_1w": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
                "top_drivers": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 7,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "driver": {"type": "string"},
                            "impact": {"type": "string", "enum": ["positive", "negative", "mixed"]},
                            "why": {"type": "string"},
                            "citations": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["driver", "impact", "why", "citations"]
                    }
                },
                "scenarios": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string", "enum": ["bull", "base", "bear"]},
                            "probability": {"type": "number", "minimum": 0, "maximum": 1},
                            "narrative": {"type": "string"},
                            "invalidated_by": {"type": "string"},
                            "citations": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "probability", "narrative", "invalidated_by", "citations"]
                    }
                },
                "watch_next": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 8,
                    "items": {"type": "string"}
                },
                "limitations": {"type": "string"}
            },
            "required": ["regime", "bias_24h", "bias_1w", "top_drivers", "scenarios", "watch_next", "limitations"]
        }
    }

    # Structured Outputs guide: the model is constrained to a JSON schema.  [oai_citation:5‡OpenAI Platform](https://platform.openai.com/docs/guides/structured-outputs?utm_source=chatgpt.com)
    resp = client.responses.create(
        model=model,
        input=prompt,
        response_format={
            "type": "json_schema",
            "json_schema": schema
        }
    )

    # The SDK returns a response object; easiest is to parse the JSON text output:
    text = resp.output_text
    return json.loads(text)
