"""LLM JSON helper — local Ollama or Azure OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

from llm_score.usage import record_usage_from_response

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

if LLM_PROVIDER == "azure":
    DEFAULT_MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
else:
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3:14b")


def parse_json_response(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _call_azure_openai_json(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
) -> dict[str, Any]:
    from openai import AzureOpenAI

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    if not endpoint or not api_key:
        raise RuntimeError("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    response = client.chat.completions.create(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    record_usage_from_response(response, model=model, provider="azure")
    raw = (response.choices[0].message.content or "").strip()
    return parse_json_response(raw)


def call_model_json(
    prompt_template: str,
    model: str = DEFAULT_MODEL,
    *,
    temperature: float = 0.1,
    system: str | None = None,
    **format_vars: str,
) -> dict[str, Any]:
    content = prompt_template.format(**format_vars)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})

    if LLM_PROVIDER == "azure":
        return _call_azure_openai_json(messages, model=model, temperature=temperature)

    import ollama

    response = ollama.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature},
    )
    record_usage_from_response(response, model=model, provider="ollama")
    raw = response["message"]["content"].strip()
    return parse_json_response(raw)
