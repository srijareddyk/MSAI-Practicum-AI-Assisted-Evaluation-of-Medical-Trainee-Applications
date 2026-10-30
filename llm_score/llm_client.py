"""Shared Ollama JSON call helper."""

from __future__ import annotations

import json
from typing import Any

import ollama

DEFAULT_MODEL = "qwen3:14b"


def parse_json_response(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}


def call_model_json(
    prompt_template: str,
    model: str = DEFAULT_MODEL,
    *,
    temperature: float = 0.1,
    **format_vars: str,
) -> dict[str, Any]:
    content = prompt_template.format(**format_vars)
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": content}],
        options={"temperature": temperature},
    )
    raw = response["message"]["content"].strip()
    return parse_json_response(raw)
