"""Provider connectors for auditable AI-output collection.

This layer is intentionally separate from the worker-agent provider in
agent.py. Worker agents modify project artifacts. Collection providers produce
research observations from an approved prompt grid.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import error as urlerror
from urllib import request


@dataclass(frozen=True)
class ProviderResponse:
    output_text: str
    provider: str
    model: str
    provider_request_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0


class ProviderError(RuntimeError):
    """Raised when a collection provider cannot return an auditable response."""


class BaseProvider:
    provider_name = "base"

    def __init__(self, *, model: str, timeout_seconds: int = 120) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str, metadata: dict[str, str]) -> ProviderResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    provider_name = "mock"

    def complete(self, prompt: str, metadata: dict[str, str]) -> ProviderResponse:
        started = time.monotonic()
        persona = metadata.get("persona", "unknown_persona")
        variant = metadata.get("prompt_variant", "unknown_variant")
        prompt_id = metadata.get("prompt_id", "unknown_prompt")
        text = (
            f"Mock grocery recommendation for {persona} under {variant}. "
            "Basket: oats, eggs, rice, beans, frozen vegetables, fruit, bread, "
            "and a low-cost protein. Budget note: choose store brands and plan "
            "leftovers. Nutrition note: include fruit, vegetables, protein, and "
            "whole grains. Feasibility note: meals should use simple preparation. "
            f"Prompt ID: {prompt_id}."
        )
        return ProviderResponse(
            output_text=text,
            provider=self.provider_name,
            model=self.model,
            provider_request_id=f"mock-{prompt_id}",
            duration_ms=int((time.monotonic() - started) * 1000),
        )


class OpenAIProvider(BaseProvider):
    provider_name = "openai"

    def complete(self, prompt: str, metadata: dict[str, str]) -> ProviderResponse:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "input": prompt,
        }
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"OpenAI HTTP {exc.code}: {detail}") from exc
        except (urlerror.URLError, TimeoutError) as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError("OpenAI returned non-JSON response") from exc

        output_text = data.get("output_text")
        if not output_text:
            chunks: list[str] = []
            for item in data.get("output", []) or []:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []) or []:
                    if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                        chunks.append(str(content.get("text", "")))
            output_text = "\n".join(chunks).strip()
        if not output_text:
            raise ProviderError("OpenAI returned no output text")

        usage = data.get("usage", {}) or {}
        return ProviderResponse(
            output_text=output_text,
            provider=self.provider_name,
            model=self.model,
            provider_request_id=str(data.get("id", "")),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            cost_usd=0.0,
            duration_ms=int((time.monotonic() - started) * 1000),
        )


def make_provider(provider: str, *, model: str, timeout_seconds: int) -> BaseProvider:
    normalized = provider.strip().lower()
    if normalized == "mock":
        return MockProvider(model=model or "mock-research-model", timeout_seconds=timeout_seconds)
    if normalized == "openai":
        return OpenAIProvider(model=model or "gpt-4.1-mini", timeout_seconds=timeout_seconds)
    raise ProviderError(f"unsupported collection provider: {provider}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
