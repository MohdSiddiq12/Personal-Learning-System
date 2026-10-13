import asyncio
import json
import logging

import httpx
import pytest
from pydantic import BaseModel, Field, SecretStr

from learnbook.api.generation import complete_model
from learnbook.api.provider import (
    CompletionResult,
    GroqProvider,
    ProviderError,
    TokenBucket,
    estimate_tokens,
)
from learnbook.config import Settings


class OutputModel(BaseModel):
    answer: str = Field(min_length=2)


def provider_settings(**values: object) -> Settings:
    return Settings(
        _env_file=None,
        groq_api_key=SecretStr("test-server-key-never-log"),
        groq_model="test-model-from-settings",
        groq_max_retries=values.pop("groq_max_retries", 0),
        groq_max_total_wait_seconds=values.pop("groq_max_total_wait_seconds", 0),
        **values,
    )


def response(
    text: str = '{"answer":"ok"}',
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    if status != 200:
        return httpx.Response(status, headers=headers)
    return httpx.Response(
        status,
        json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        },
        headers=headers,
    )


def test_429_retry_after_then_success_uses_server_key_header() -> None:
    seen: list[httpx.Request] = []
    answers = [response(status=429, headers={"Retry-After": "0"}), response()]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answers.pop(0)

    provider = GroqProvider(
        provider_settings(groq_max_retries=1), transport=httpx.MockTransport(handler)
    )
    result = asyncio.run(
        provider.complete([{"role": "user", "content": "small prompt"}], 50)
    )

    assert result == CompletionResult('{"answer":"ok"}', 10, 3)
    assert len(seen) == 2
    assert seen[0].headers["Authorization"] == "Bearer test-server-key-never-log"
    assert "test-model-from-settings" in seen[0].read().decode()


def test_repeated_429_returns_rate_limited_without_leaking_prompt_or_key(
    caplog,
) -> None:
    provider = GroqProvider(
        provider_settings(groq_max_retries=1),
        transport=httpx.MockTransport(
            lambda _: response(status=429, headers={"Retry-After": "0"})
        ),
    )
    with caplog.at_level(logging.WARNING), pytest.raises(ProviderError) as exc:
        asyncio.run(
            provider.complete([{"role": "user", "content": "private prompt"}], 50)
        )

    assert exc.value.error_code == "rate_limited"
    assert "private prompt" not in caplog.text
    assert "test-server-key-never-log" not in caplog.text


def test_json_validation_repairs_once_and_parses_code_fence() -> None:
    contents = ["not json", '```json\n{"answer":"fixed"}\n```']
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return response(contents.pop(0))

    provider = GroqProvider(provider_settings(), transport=httpx.MockTransport(handler))
    model, _ = asyncio.run(
        complete_model(
            provider,
            [{"role": "system", "content": "return answer"}],
            OutputModel,
            max_output_tokens=50,
            json_mode=False,
        )
    )

    assert model.answer == "fixed"
    assert len(requests) == 2
    assert "Validation summary" in str(requests[1]["messages"])


def test_invalid_output_after_one_repair_returns_friendly_code() -> None:
    provider = GroqProvider(
        provider_settings(),
        transport=httpx.MockTransport(lambda _: response("still not JSON")),
    )
    with pytest.raises(ProviderError) as exc:
        asyncio.run(
            complete_model(
                provider,
                [{"role": "system", "content": "schema"}],
                OutputModel,
                max_output_tokens=50,
                json_mode=False,
            )
        )
    assert exc.value.error_code == "invalid_output"


def test_timeout_and_server_errors_retry_then_fail_without_logging(caplog) -> None:
    calls = 0

    def timeout(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("private prompt and test-server-key-never-log")

    provider = GroqProvider(provider_settings(), transport=httpx.MockTransport(timeout))
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(ProviderError) as timeout_error,
    ):
        asyncio.run(
            provider.complete([{"role": "user", "content": "private prompt"}], 50)
        )
    assert timeout_error.value.error_code == "provider_unavailable"
    assert calls == 1
    assert "private prompt" not in caplog.text
    assert "test-server-key-never-log" not in caplog.text

    provider = GroqProvider(
        provider_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(503)),
    )
    with pytest.raises(ProviderError) as server_error:
        asyncio.run(provider.complete([{"role": "user", "content": "prompt"}], 50))
    assert server_error.value.error_code == "provider_unavailable"


def test_pacing_estimate_and_request_budget_are_enforced() -> None:
    messages = [{"role": "user", "content": "x" * 350}]
    assert estimate_tokens(messages, 100) == 200
    bucket = TokenBucket(200)
    asyncio.run(bucket.acquire(200))
    assert bucket.tokens < 1

    too_small = GroqProvider(
        provider_settings(groq_max_request_tokens=150),
        transport=httpx.MockTransport(lambda _: response()),
    )
    with pytest.raises(ProviderError) as exc:
        asyncio.run(too_small.complete(messages, 100))
    assert exc.value.error_code == "invalid_output"

    json_suffix_cap = GroqProvider(
        provider_settings(groq_max_request_tokens=151),
        transport=httpx.MockTransport(lambda _: response()),
    )
    with pytest.raises(ProviderError) as json_suffix_error:
        asyncio.run(json_suffix_cap.complete(messages, 100, json_mode=False))
    assert json_suffix_error.value.error_code == "invalid_output"


def test_json_mode_is_requested_only_when_enabled() -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return response()

    provider = GroqProvider(provider_settings(), transport=httpx.MockTransport(handler))
    asyncio.run(provider.complete([{"role": "user", "content": "prompt"}], 50, True))
    assert payloads[0]["response_format"] == {"type": "json_object"}
