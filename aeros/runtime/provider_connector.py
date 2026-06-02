"""Provider connectors for auditable AI-output collection.

This layer is intentionally separate from the worker-agent provider in
agent.py. Worker agents modify project artifacts. Collection providers produce
research observations from an approved prompt grid.
"""

from __future__ import annotations

import json
import os
import tempfile
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


class ClaudeCLIProvider(BaseProvider):
    """Collect real responses via the authenticated `claude` CLI (no API key).

    Reuses the user's Claude subscription auth, exactly like the worker-agent
    runner. CLAUDECODE is dropped so the call is not blocked as a nested session.
    Cost is the notional total_cost_usd the CLI reports (subscription-covered;
    informational, recorded for provenance).
    """

    provider_name = "claude-cli"

    def complete(self, prompt: str, metadata: dict[str, str]) -> ProviderResponse:
        import shutil
        import subprocess

        binary = shutil.which("claude")
        if not binary:
            raise ProviderError("`claude` CLI not found on PATH")
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        prompt_id = metadata.get("prompt_id", "unknown_prompt")
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [binary, "-p", prompt, "--output-format", "json"],
                capture_output=True, text=True, timeout=self.timeout_seconds, env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"claude CLI timed out after {self.timeout_seconds}s") from exc

        try:
            data = json.loads((proc.stdout or "").strip())
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError(
                f"claude CLI returned non-JSON (rc={proc.returncode}): "
                f"{(proc.stderr or proc.stdout or '').strip()[:200]}"
            ) from exc

        if data.get("is_error") or proc.returncode != 0:
            raise ProviderError(f"claude CLI error: {str(data.get('result',''))[:200]}")

        usage = data.get("usage", {}) or {}
        text = str(data.get("result", "")).strip()
        if not text:
            raise ProviderError("claude CLI returned no result text")
        return ProviderResponse(
            output_text=text,
            provider=self.provider_name,
            model=self.model or "claude",
            provider_request_id=str(data.get("session_id", f"claude-{prompt_id}")),
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            cost_usd=float(data.get("total_cost_usd", 0.0) or 0.0),
            duration_ms=int((time.monotonic() - started) * 1000),
        )


class CodexCLIProvider(BaseProvider):
    """Collect real responses via the authenticated Codex CLI (no API key)."""

    provider_name = "codex-cli"

    def complete(self, prompt: str, metadata: dict[str, str]) -> ProviderResponse:
        import shutil
        import subprocess

        binary = shutil.which("codex")
        if not binary:
            fallback = "/Applications/Codex.app/Contents/Resources/codex"
            binary = fallback if os.path.exists(fallback) else ""
        if not binary:
            raise ProviderError("`codex` CLI not found")

        prompt_id = metadata.get("prompt_id", "unknown_prompt")
        collection_prompt = (
            "You are being used as a data-collection model for an AEROS research audit.\n"
            "Return only the requested grocery recommendation text.\n"
            "Do not inspect files. Do not run commands. Do not modify files.\n"
            "Do not include meta commentary about being Codex.\n\n"
            f"{prompt}"
        )
        started = time.monotonic()
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as handle:
            output_path = handle.name
        try:
            cmd = [
                binary,
                "-a",
                "never",
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--output-last-message",
                output_path,
            ]
            if self.model:
                cmd.extend(["--model", self.model])
            cmd.append(collection_prompt)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            output_text = ""
            try:
                with open(output_path, encoding="utf-8") as out:
                    output_text = out.read().strip()
            except OSError:
                output_text = ""
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"codex CLI timed out after {self.timeout_seconds}s") from exc
        finally:
            try:
                os.unlink(output_path)
            except OSError:
                pass

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:500]
            raise ProviderError(f"codex CLI error (rc={proc.returncode}): {detail}")
        if not output_text:
            detail = (proc.stderr or proc.stdout or "").strip()[:500]
            raise ProviderError(f"codex CLI returned no final message: {detail}")

        return ProviderResponse(
            output_text=output_text,
            provider=self.provider_name,
            model=self.model or "codex",
            provider_request_id=f"codex-{prompt_id}-{int(time.time())}",
            duration_ms=int((time.monotonic() - started) * 1000),
        )


def make_provider(provider: str, *, model: str, timeout_seconds: int) -> BaseProvider:
    normalized = provider.strip().lower()
    if normalized == "mock":
        return MockProvider(model=model or "mock-research-model", timeout_seconds=timeout_seconds)
    if normalized == "openai":
        return OpenAIProvider(model=model or "gpt-4.1-mini", timeout_seconds=timeout_seconds)
    if normalized in {"claude-cli", "claude"}:
        return ClaudeCLIProvider(model=model or "claude", timeout_seconds=timeout_seconds)
    if normalized in {"codex-cli", "codex"}:
        codex_model = "" if model in {"", "mock-research-model"} else model
        return CodexCLIProvider(model=codex_model, timeout_seconds=timeout_seconds)
    raise ProviderError(f"unsupported collection provider: {provider}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
