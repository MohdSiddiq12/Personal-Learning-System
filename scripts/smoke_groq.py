"""Send one minimal request to verify Groq credentials and connectivity."""

import asyncio

import httpx

from learnbook.config import Settings


async def main() -> int:
    settings = Settings()
    key = settings.groq_api_key
    model = settings.groq_model
    if key is None or not key.get_secret_value().strip() or not model:
        print("HTTP status: not sent (Groq configuration missing)")
        return 1

    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key.get_secret_value()}"},
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": "Reply with the single word OK."}
                ],
                "max_tokens": 8,
                "temperature": 0,
            },
        )

    print(f"HTTP status: {response.status_code}")
    if not response.is_success:
        return 1
    try:
        usage = response.json()["usage"]
        prompt_tokens = int(usage["prompt_tokens"])
        completion_tokens = int(usage["completion_tokens"])
    except (ValueError, KeyError, TypeError):
        print("Token usage: unavailable")
        return 1
    print(f"Token usage: prompt={prompt_tokens}, completion={completion_tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
