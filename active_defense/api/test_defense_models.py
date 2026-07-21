"""Sanity-check models used by the defense; all calls are logged to api/api_logs."""
from __future__ import annotations

import argparse
import json
import re

from code.internal_client import client_for_model


def check(model: str) -> dict:
    client = client_for_model(model)
    plain = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": "Return exactly: API_OK"}],
        max_tokens=32)
    structured = client.chat.completions.create(
        model=model,
        messages=[{"role": "user",
                   "content": 'Return only JSON with ok=true and role="contractor".'}],
        response_format={"type": "json_object"}, max_tokens=64)
    tools = [{"type": "function", "function": {
        "name": "lookup_record", "description": "Read one record",
        "parameters": {"type": "object", "properties": {
            "record_id": {"type": "string"}}, "required": ["record_id"],
            "additionalProperties": False}}}]
    called = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Use lookup_record to read record R-7."}],
        tools=tools, tool_choice="auto", max_tokens=64)
    calls = called.choices[0].message.tool_calls or []
    structured_text = structured.choices[0].message.content or "{}"
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", structured_text, re.S)
    return {
        "model": model,
        "plain": (plain.choices[0].message.content or "").strip() == "API_OK",
        "json": json.loads(fenced.group(1) if fenced else structured_text),
        "tool_calls": [{"name": item.function.name,
                        "arguments": json.loads(item.function.arguments)} for item in calls],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", help="OpenAI-compatible model names")
    args = parser.parse_args()
    for model in args.models:
        try:
            print(json.dumps(check(model), ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"model": model, "error": str(exc)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
