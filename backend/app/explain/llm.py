"""LLM providers behind one small interface (ADR-0004, ADR-0007).

GroqProvider calls Groq's OpenAI-compatible chat API with JSON-schema structured output and still parses and
checks the JSON itself. Any transport or format problem raises LLMError; callers fall back to the template.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class Completion:
    content: dict
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int  # from the first attempt to the answer, including waits for the rate limit
    waited_ms: int = 0  # of which spent waiting for the rate limit


class LLMProvider(Protocol):
    model: str

    def complete_json(self, messages: list[dict[str, str]], schema: dict, name: str, *,
                      effort: str = "medium", max_tokens: int = 4000) -> Completion: ...


class GroqProvider:
    def __init__(self, api_key: str, model: str, timeout: float = 60.0, client: httpx.Client | None = None,
                 max_retries: int = 4, max_wait: float = 60.0):
        if not api_key:
            raise LLMError("GROQ_API_KEY is not set")
        self.model = model
        self.max_retries = max_retries
        self.max_wait = max_wait
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def complete_json(self, messages: list[dict[str, str]], schema: dict, name: str, *,
                      effort: str = "medium", max_tokens: int = 4000) -> Completion:
        body = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
            "temperature": 0.3,
            "max_completion_tokens": max_tokens,
        }
        if self.model.startswith("openai/gpt-oss"):
            body["reasoning_effort"] = effort
        started = time.perf_counter()
        waited = 0.0
        for attempt in range(self.max_retries + 1):
            try:
                r = self._client.post(GROQ_URL, headers=self._headers, json=body)
            except httpx.HTTPError as exc:
                raise LLMError(f"request failed: {type(exc).__name__}") from exc
            if r.status_code != 429 or attempt == self.max_retries:
                break
            # Rate limit (tokens or requests per minute): wait as long as Groq asks, within reason.
            pause = min(float(r.headers.get("retry-after", "5") or 5), self.max_wait)
            time.sleep(pause)
            waited += pause
        latency = round((time.perf_counter() - started) * 1000)
        if r.status_code != 200:
            # The error body can echo the request; keep only the type, never health data.
            try:
                kind = r.json().get("error", {}).get("type") or r.json().get("error", {}).get("code")
            except ValueError:
                kind = None
            raise LLMError(f"HTTP {r.status_code} {kind or ''}".strip())
        data = r.json()
        try:
            content = json.loads(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError("response was not the expected JSON") from exc
        if not isinstance(content, dict):
            raise LLMError("response JSON is not an object")
        usage = data.get("usage") or {}
        return Completion(content, data.get("model", self.model), int(usage.get("prompt_tokens", 0)),
                          int(usage.get("completion_tokens", 0)), latency, round(waited * 1000))


class ScriptedProvider:
    """Test double: returns queued responses (a dict, or an Exception to raise) in order."""

    def __init__(self, *responses: dict | Exception, model: str = "scripted"):
        self.model = model
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete_json(self, messages, schema, name, *, effort="medium", max_tokens=4000) -> Completion:  # noqa: ANN001
        self.calls.append(messages)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return Completion(response, self.model, 100, 50, 5)
