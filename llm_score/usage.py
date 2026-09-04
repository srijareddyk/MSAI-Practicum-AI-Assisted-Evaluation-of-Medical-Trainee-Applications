"""Accumulate Azure/OpenAI token usage for a screening run."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

# Global Standard list prices (USD per 1M tokens), verified Aug 2026.
_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}

_current: ContextVar["UsageTracker | None"] = ContextVar("llm_usage", default=None)


def _rates_for(model: str) -> tuple[float, float]:
    key = (model or "").strip().lower()
    if key in _PRICES:
        return _PRICES[key]
    for name, pair in _PRICES.items():
        if name in key:
            return pair
    return _PRICES["gpt-4.1-mini"]


@dataclass
class UsageTracker:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    model: str = ""
    provider: str = ""
    cached_prompt_tokens: int = 0

    def add(
        self,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cached_prompt_tokens: int = 0,
        model: str = "",
        provider: str = "",
    ) -> None:
        self.prompt_tokens += int(prompt_tokens or 0)
        self.completion_tokens += int(completion_tokens or 0)
        added_total = int(total_tokens or 0)
        self.total_tokens += added_total or (int(prompt_tokens or 0) + int(completion_tokens or 0))
        self.cached_prompt_tokens += int(cached_prompt_tokens or 0)
        self.calls += 1
        if model:
            self.model = model
        if provider:
            self.provider = provider

    def snapshot(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "calls": self.calls,
            "cached_prompt_tokens": self.cached_prompt_tokens,
        }

    def delta(self, before: dict[str, int]) -> "UsageTracker":
        return UsageTracker(
            prompt_tokens=self.prompt_tokens - before["prompt_tokens"],
            completion_tokens=self.completion_tokens - before["completion_tokens"],
            total_tokens=self.total_tokens - before["total_tokens"],
            calls=self.calls - before["calls"],
            cached_prompt_tokens=self.cached_prompt_tokens - before["cached_prompt_tokens"],
            model=self.model,
            provider=self.provider,
        )

    def estimated_usd(self) -> float:
        in_rate, out_rate = _rates_for(self.model)
        billed_prompt = max(0, self.prompt_tokens - self.cached_prompt_tokens)
        cached_rate = in_rate * 0.25
        return (
            billed_prompt * in_rate / 1_000_000
            + self.cached_prompt_tokens * cached_rate / 1_000_000
            + self.completion_tokens * out_rate / 1_000_000
        )

    def to_dict(self) -> dict[str, Any]:
        in_rate, out_rate = _rates_for(self.model)
        usd = self.estimated_usd()
        return {
            "provider": self.provider or None,
            "model": self.model or None,
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached_prompt_tokens": self.cached_prompt_tokens,
            "estimated_usd": round(usd, 6),
            "pricing": {
                "input_usd_per_million": in_rate,
                "output_usd_per_million": out_rate,
                "note": "Azure Global Standard list price; Student credit is billed in USD.",
            },
        }


def pricing_catalog() -> list[dict[str, Any]]:
    return [
        {
            "model": name,
            "input_usd_per_million": rates[0],
            "output_usd_per_million": rates[1],
        }
        for name, rates in _PRICES.items()
    ]


def estimate_usd_for(prompt_tokens: int, completion_tokens: int, model: str = "gpt-4.1-mini") -> float:
    in_rate, out_rate = _rates_for(model)
    return prompt_tokens * in_rate / 1_000_000 + completion_tokens * out_rate / 1_000_000


def start_usage_tracker(provider: str = "", model: str = "") -> UsageTracker:
    tracker = UsageTracker(provider=provider, model=model)
    _current.set(tracker)
    return tracker


def current_usage() -> UsageTracker | None:
    return _current.get()


def record_usage_from_response(response: Any, *, model: str, provider: str) -> None:
    tracker = _current.get()
    if tracker is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        if "prompt_eval_count" in response or "eval_count" in response:
            tracker.add(
                prompt_tokens=int(response.get("prompt_eval_count") or 0),
                completion_tokens=int(response.get("eval_count") or 0),
                model=model,
                provider=provider,
            )
            return
        usage = response.get("usage")
    prompt = completion = total = cached = 0
    if usage is not None and not isinstance(usage, int):
        prompt = int(getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None) or 0)
        completion = int(
            getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None) or 0
        )
        total = int(getattr(usage, "total_tokens", None) or 0)
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = int(getattr(details, "cached_tokens", None) or 0)
    tracker.add(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        cached_prompt_tokens=cached,
        model=model,
        provider=provider,
    )
