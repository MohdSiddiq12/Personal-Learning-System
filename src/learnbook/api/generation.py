"""Validated structured output and provider-usage callbacks."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from learnbook.api.provider import (
    CompletionResult,
    LLMProvider,
    ProviderError,
    parse_json_response,
)

ModelT = TypeVar("ModelT", bound=BaseModel)
UsageCallback = Callable[[int, int], Awaitable[None]]


def _validation_summary(error: ValidationError | ValueError) -> str:
    if isinstance(error, ValidationError):
        parts = [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors(include_input=False)[:5]
        ]
        return "; ".join(parts)[:500] or "Output did not match the schema."
    return str(error)[:500]


async def complete_model(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    model_type: type[ModelT],
    *,
    max_output_tokens: int,
    json_mode: bool,
    on_usage: UsageCallback | None = None,
) -> tuple[ModelT, CompletionResult]:
    previous_error: ValidationError | ValueError | None = None
    current_messages = messages
    for attempt in range(2):
        result = await provider.complete(current_messages, max_output_tokens, json_mode)
        if on_usage:
            await on_usage(result.prompt_tokens, result.completion_tokens)
        try:
            parsed = parse_json_response(result.text)
            return model_type.model_validate(parsed), result
        except (ValueError, ValidationError) as error:
            previous_error = error
            if attempt == 0:
                summary = _validation_summary(error)
                current_messages = [
                    *messages,
                    {"role": "assistant", "content": result.text[:12000]},
                    {
                        "role": "user",
                        "content": (
                            "Repair the JSON output to satisfy the requested schema. "
                            "Validation summary: " + summary
                        ),
                    },
                ]
    raise ProviderError(
        "invalid_output",
        "The learning service returned an invalid result. Please retry.",
    ) from previous_error
