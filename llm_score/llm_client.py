"""Shared LLM JSON call helper: Google Gemini (default) or local Ollama.

Provider is picked from the environment (a `.env` file at the repo root is loaded):
  LLM_PROVIDER=gemini|ollama   (default: gemini when GEMINI_API_KEY is set, else ollama)
  GEMINI_API_KEY=...           (GOOGLE_API_KEY also works)
  GEMINI_MODEL=gemini-3.8-flash
  OLLAMA_MODEL=qwen3:8b
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # dotenv is optional; plain env vars still work
    pass


def _gemini_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or ("gemini" if _gemini_key() else "ollama")).strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
DEFAULT_MODEL = GEMINI_MODEL if LLM_PROVIDER == "gemini" else OLLAMA_MODEL

THINK = False
KEEP_ALIVE = "15m"
NUM_CTX = 4096
REPEAT_LAST_N = 256
# Gemini thinking models spend output tokens on internal thinking, so the per-call cap is
# raised to leave room for both the thinking and the JSON answer.
GEMINI_MIN_OUTPUT_TOKENS = 8192


def generation_settings() -> dict[str, Any]:
    """Options actually passed to the model. The developer tab reads this."""
    if LLM_PROVIDER == "gemini":
        return {
            "provider": "gemini",
            "think": True,
            "keep_alive": "n/a (hosted)",
            "num_ctx": 1_000_000,
            "repeat_last_n": 0,
            "json_mode": True,
            "attempts": [
                {
                    "temperature": 0.1,
                    "repeat_penalty": 0,
                    "num_predict": f"max(call's max tokens, {GEMINI_MIN_OUTPUT_TOKENS})",
                },
                {
                    "temperature": 0.3,
                    "repeat_penalty": 0,
                    "num_predict": f"max(call's max tokens, {GEMINI_MIN_OUTPUT_TOKENS})",
                    "when": "only if the first reply is not parseable JSON",
                },
            ],
        }
    return {
        "provider": "ollama",
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


_gemini_client = None


def _gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        key = _gemini_key()
        if not key:
            raise RuntimeError("Set GEMINI_API_KEY in .env")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


def check_llm(model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """Reachability check for the health endpoint."""
    if LLM_PROVIDER == "gemini":
        try:
            names = [
                (m.name or "").removeprefix("models/")
                for m in _gemini().models.list()
                if "gemini" in (m.name or "")
            ]
            return {
                "provider": "gemini",
                "ok": True,
                "available": model in names,
                "models": names,
                "requested": model,
            }
        except Exception as exc:  # noqa: BLE001 — surface status to UI
            return {"provider": "gemini", "ok": False, "available": False, "error": str(exc), "requested": model}
    try:
        import ollama

        names = [m.get("model") or m.get("name") or "" for m in ollama.list().get("models", [])]
        names = [n for n in names if n]
        available = any(model in n or n.startswith(f"{model}:") for n in names)
        return {"provider": "ollama", "ok": True, "available": available, "models": names, "requested": model}
    except Exception as exc:  # noqa: BLE001
        return {"provider": "ollama", "ok": False, "available": False, "error": str(exc), "requested": model}


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
    """The user message the model receives, after placeholders are filled."""
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
    if LLM_PROVIDER == "gemini":
        return _call_gemini_json(content, model, temperature=temperature, max_tokens=max_tokens)
    return _call_ollama_json(content, model, temperature=temperature, max_tokens=max_tokens)


def _call_gemini_json(content: str, model: str, *, temperature: float, max_tokens: int) -> dict[str, Any]:
    from google.genai import types

    last_error = "Model returned no parseable JSON"
    for temp in (temperature, 0.3):
        try:
            response = _gemini().models.generate_content(
                model=model,
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=temp,
                    max_output_tokens=max(max_tokens, GEMINI_MIN_OUTPUT_TOKENS),
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:  # noqa: BLE001 — surface a short reason and retry once
            last_error = str(exc)
            continue
        parsed = parse_json_response((response.text or "").strip())
        if parsed:
            return parsed
        last_error = "Model returned no parseable JSON"
    return {"error": last_error}


def _call_ollama_json(content: str, model: str, *, temperature: float, max_tokens: int) -> dict[str, Any]:
    import ollama

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
