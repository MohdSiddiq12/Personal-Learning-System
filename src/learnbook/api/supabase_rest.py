"""Small server-only Supabase REST and Storage client."""

from typing import Any

import httpx
from fastapi import HTTPException

from learnbook.config import Settings


class SupabaseRest:
    """Use the service role only after an access token has been verified."""

    def __init__(self, settings: Settings) -> None:
        if not (
            settings.supabase_url
            and settings.supabase_anon_key
            and settings.supabase_service_role_key
        ):
            raise HTTPException(
                status_code=503,
                detail="Online storage is not configured for this deployment.",
            )
        self.base_url = settings.supabase_url.rstrip("/")
        self.anon_key = settings.supabase_anon_key.get_secret_value()
        self.service_key = settings.supabase_service_role_key.get_secret_value()

    async def verify_user(self, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/auth/v1/user",
                    headers={
                        "apikey": self.anon_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                )
            except httpx.HTTPError as error:
                raise HTTPException(
                    status_code=503,
                    detail="Sign-in service is temporarily unavailable.",
                ) from error
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Please sign in again.")
        user_id = response.json().get("id")
        if not isinstance(user_id, str):
            raise HTTPException(status_code=401, detail="Please sign in again.")
        return user_id

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: Any = None,
        content: bytes | None = None,
        content_type: str | None = None,
        prefer: str | None = None,
        allow_not_found: bool = False,
    ) -> httpx.Response:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=45) as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    params=params,
                    json=json,
                    content=content,
                    headers=headers,
                )
            except httpx.HTTPError as error:
                raise HTTPException(
                    status_code=503,
                    detail="Online storage is temporarily unavailable.",
                ) from error
        if response.is_error and not (allow_not_found and response.status_code == 404):
            if path in {
                "/rest/v1/rpc/create_generation_job",
                "/rest/v1/rpc/retry_generation_job",
            }:
                try:
                    rpc_message = response.json().get("message", "")
                except (ValueError, AttributeError):
                    rpc_message = ""
                if rpc_message == "active_job":
                    raise HTTPException(
                        status_code=409, detail="A learning job is already running."
                    )
                if rpc_message == "budget_exhausted":
                    raise HTTPException(
                        status_code=429,
                        detail="Daily capacity reached. Please try again tomorrow.",
                    )
                if rpc_message == "quota_exceeded":
                    raise HTTPException(
                        status_code=429,
                        detail="Your daily generation limit was reached.",
                    )
            raise HTTPException(
                status_code=502,
                detail="Online storage could not complete the request.",
            )
        return response

    async def reserve_summary(self, user_id: str, settings: Settings) -> bool:
        response = await self.request(
            "POST",
            "/rest/v1/rpc/reserve_book_summary",
            json={
                "p_user_id": user_id,
                "p_daily_limit": settings.ai_daily_summary_limit,
                "p_monthly_limit": settings.ai_monthly_summary_limit,
            },
        )
        return response.json() is True

    async def reserve_upload(self, user_id: str, settings: Settings) -> bool:
        response = await self.request(
            "POST",
            "/rest/v1/rpc/reserve_book_upload",
            json={
                "p_user_id": user_id,
                "p_daily_limit": settings.upload_daily_limit,
            },
        )
        return response.json() is True
