"""Shared Ollama JSON call helper."""

from __future__ import annotations

import json
import re
from typing import Any

import ollama

DEFAULT_MODEL = "qwen3:8b"
THINK = False
KEEP_ALIVE = "15m"
NUM_CTX = 4096
REPEAT_LAST_N = 256


def generation_settings() -> dict[str, Any]:
    """Options actually passed to Ollama. The developer tab reads this."""
    return {
        "think": THINK,
        "keep_alive": KEEP_ALIVE,
        "num_ctx": NUM_CTX,
        "repeat_last_n": REPEAT_LAST_N,
        "json_mode": False,
        "attempts": [
            {
                "temperature": 0.1,
                "repeat_penalty": 1.08,
                "num_predict": "the call's max tokens",
            },
            {
                "temperature": 0.3,
                "repeat_penalty": 1.25,
                "num_predict": "500, or the call's max tokens if that is lower",
                "when": "only if the first reply is not parseable JSON",
            },
        ],
    }


def parse_json_response(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}


def tighten_text(text: str) -> str:
    """PDF extraction often doubles spaces. That wastes tokens and can make the model loop."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def render_user_prompt(prompt_template: str, **format_vars: str) -> str:
    """The user message Ollama receives, after placeholders are filled."""
    return tighten_text(prompt_template.format(**format_vars))


def call_model_json(
    prompt_template: str,
    model: str = DEFAULT_MODEL,
    *,
    temperature: float = 0.1,
    max_tokens: int = 700,
    **format_vars: str,
) -> dict[str, Any]:
    content = render_user_prompt(prompt_template, **format_vars)
    # JSON mode makes Qwen repeat the same token until Ollama aborts with HTTP 500.
    attempts = (
        {"temperature": temperature, "num_predict": max_tokens, "repeat_penalty": 1.08},
        {"temperature": 0.3, "num_predict": min(500, max_tokens), "repeat_penalty": 1.25},
    )
    last_error = "Model returned no parseable JSON"
    for options in attempts:
        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": content}],
                think=THINK,
                keep_alive=KEEP_ALIVE,
                options={
                    "temperature": options["temperature"],
                    "num_predict": options["num_predict"],
                    "num_ctx": NUM_CTX,
                    "repeat_penalty": options["repeat_penalty"],
                    "repeat_last_n": REPEAT_LAST_N,
                },
            )
        except Exception as exc:  # noqa: BLE001 — surface a short reason and retry once
            last_error = str(exc)
            continue
        raw = (response.get("message") or {}).get("content") or ""
        parsed = parse_json_response(raw.strip())
        if parsed:
            return parsed
        last_error = "Model returned no parseable JSON"
    return {"error": last_error}
