"""Server-side Groq-compatible chat completion client and process pacing."""

import asyncio
import json
import logging
import math
import random
import re
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Protocol

import httpx

from learnbook.config import Settings

logger = logging.getLogger(__name__)
_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_UNAVAILABLE_MESSAGE = "The learning service is temporarily unavailable. Try again."
_RATE_LIMITED_MESSAGE = "The learning service is busy. Please try again shortly."


class ProviderError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.user_message = message


@dataclass(frozen=True)
class CompletionResult:
    text: str
    prompt_tokens: int
    completion_tokens: int


class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict[str, str]],
        max_output_tokens: int,
        json_mode: bool,
    ) -> CompletionResult: ...


def estimate_tokens(messages: list[dict[str, str]], output_tokens: int) -> int:
    characters = sum(len(message.get("content", "")) for message in messages)
    return math.ceil(characters / 3.5) + output_tokens


class TokenBucket:
    """Single-process token bucket used with the single-instance worker design."""

    def __init__(self, tokens_per_minute: int) -> None:
        self.capacity = float(tokens_per_minute)
        self.tokens = float(tokens_per_minute)
        self.updated_at = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int) -> None:
        if estimated_tokens > self.capacity:
            raise ProviderError(
                "invalid_output",
                "This generation request is too large. Try a smaller source section.",
            )
        async with self.lock:
            while True:
                now = time.monotonic()
                self.tokens = min(
                    self.capacity,
                    self.tokens + (now - self.updated_at) * self.capacity / 60,
                )
                self.updated_at = now
                if self.tokens >= estimated_tokens:
                    self.tokens -= estimated_tokens
                    return
                await asyncio.sleep(
                    (estimated_tokens - self.tokens) * 60 / self.capacity
                )


class GroqProvider:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        bucket: TokenBucket | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.bucket = bucket or TokenBucket(settings.groq_tpm_limit)
        self._single_flight = asyncio.Semaphore(1)

    def _api_key(self) -> str:
        value = self.settings.groq_api_key
        if not value or not value.get_secret_value().strip():
            raise ProviderError(
                "provider_unavailable", "The learning service is not configured yet."
            )
        return value.get_secret_value()

    def _model(self) -> str:
        value = self.settings.groq_model
        if not value or not value.strip():
            raise ProviderError(
                "provider_unavailable", "The learning service is not configured yet."
            )
        return value.strip()

    @staticmethod
    def _retry_after(response: httpx.Response, attempt: int) -> float:
        raw = response.headers.get("retry-after")
        if raw:
            try:
                return max(0.0, float(raw))
            except ValueError:
                try:
                    return max(
                        0.0,
                        (parsedate_to_datetime(raw).timestamp() - time.time()),
                    )
                except (TypeError, ValueError, OverflowError):
                    pass
        for name in ("x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
            raw = response.headers.get(name)
            if raw:
                match = re.fullmatch(r"([\d.]+)(ms|s|m)?", raw.strip(), re.I)
                if match:
                    scale = {"ms": 0.001, "s": 1, "m": 60, None: 1}[
                        match.group(2).lower() if match.group(2) else None
                    ]
                    return max(0.0, float(match.group(1)) * scale)
        return min(30.0, 0.5 * (2**attempt)) + random.uniform(0, 0.25)

    async def complete(
        self,
        messages: list[dict[str, str]],
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> CompletionResult:
        key = self._api_key()
        model = self._model()
        if not messages or max_output_tokens < 1:
            raise ValueError(
                "Messages and a positive output token budget are required."
            )
        request_messages = (
            messages
            if json_mode
            else [
                *messages,
                {
                    "role": "user",
                    "content": "Return only valid JSON. Do not use markdown.",
                },
            ]
        )
        estimated = estimate_tokens(request_messages, max_output_tokens)
        if estimated > self.settings.groq_max_request_tokens:
            raise ProviderError(
                "invalid_output",
                "This generation request is too large. Try a smaller source section.",
            )
        await self.bucket.acquire(estimated)
        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        else:
            payload["messages"] = request_messages

        total_wait = 0.0
        retries = self.settings.groq_max_retries
        async with self._single_flight:
            async with httpx.AsyncClient(
                timeout=self.settings.groq_timeout_seconds, transport=self.transport
            ) as client:
                for attempt in range(retries + 1):
                    try:
                        response = await client.post(
                            _CHAT_URL,
                            headers={"Authorization": f"Bearer {key}"},
                            json=payload,
                        )
                    except httpx.HTTPError:
                        if attempt >= retries:
                            raise ProviderError(
                                "provider_unavailable",
                                _UNAVAILABLE_MESSAGE,
                            ) from None
                        delay = min(10.0, 0.5 * (2**attempt)) + random.uniform(0, 0.25)
                        if (
                            total_wait + delay
                            > self.settings.groq_max_total_wait_seconds
                        ):
                            raise ProviderError(
                                "provider_unavailable",
                                _UNAVAILABLE_MESSAGE,
                            ) from None
                        total_wait += delay
                        await asyncio.sleep(delay)
                        continue
                    if response.status_code == 429:
                        if attempt >= retries:
                            raise ProviderError(
                                "rate_limited",
                                _RATE_LIMITED_MESSAGE,
                            )
                        delay = self._retry_after(response, attempt)
                        if (
                            total_wait + delay
                            > self.settings.groq_max_total_wait_seconds
                        ):
                            raise ProviderError(
                                "rate_limited",
                                _RATE_LIMITED_MESSAGE,
                            )
                        total_wait += delay
                        await asyncio.sleep(delay)
                        continue
                    if response.status_code >= 500:
                        if attempt >= retries:
                            raise ProviderError(
                                "provider_unavailable",
                                _UNAVAILABLE_MESSAGE,
                            )
                        delay = min(10.0, 0.5 * (2**attempt)) + random.uniform(0, 0.25)
                        if (
                            total_wait + delay
                            > self.settings.groq_max_total_wait_seconds
                        ):
                            raise ProviderError(
                                "provider_unavailable",
                                _UNAVAILABLE_MESSAGE,
                            )
                        total_wait += delay
                        await asyncio.sleep(delay)
                        continue
                    if response.is_error:
                        logger.warning(
                            "Groq request rejected: status=%d", response.status_code
                        )
                        raise ProviderError(
                            "provider_unavailable",
                            "The learning service could not complete this request.",
                        )
                    try:
                        body = response.json()
                        text = body["choices"][0]["message"]["content"]
                        usage = body["usage"]
                        prompt_tokens = int(usage["prompt_tokens"])
                        completion_tokens = int(usage["completion_tokens"])
                    except (ValueError, KeyError, IndexError, TypeError):
                        raise ProviderError(
                            "invalid_output",
                            "The learning service returned an unreadable response.",
                        ) from None
                    if (
                        not isinstance(text, str)
                        or prompt_tokens < 0
                        or completion_tokens < 0
                    ):
                        raise ProviderError(
                            "invalid_output",
                            "The learning service returned an unreadable response.",
                        )
                    return CompletionResult(text, prompt_tokens, completion_tokens)
        raise ProviderError(
            "provider_unavailable", "The learning service is unavailable."
        )


def parse_json_response(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Response was not JSON.") from None
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("JSON response must be an object.")
    return parsed
