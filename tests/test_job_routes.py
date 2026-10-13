import asyncio
from datetime import UTC, datetime, timedelta

import httpx

from learnbook.api.main import (
    create_app,
    current_user_id,
    get_backend,
    get_provider,
    get_settings,
)
from learnbook.api.provider import CompletionResult
from learnbook.config import Settings

USER_ID = "8799ef5a-a9ef-4bea-b8ec-0a3f185b4c0b"
OTHER_ID = "c737a833-4717-49cf-a41c-62e2e4fe64fb"
BOOK_ID = "9f267ded-b043-46a9-9e5a-53c2665d37df"
JOB_ID = "e16230ab-85fa-4d12-8078-8341e6da88fc"


def job(status: str = "queued", *, owner: str = USER_ID, heartbeat: str | None = None):
    now = datetime.now(UTC).isoformat()
    return {
        "id": JOB_ID,
        "user_id": owner,
        "book_id": BOOK_ID,
        "topic_id": None,
        "kind": "map",
        "status": status,
        "step": status,
        "progress_pct": 0,
        "total_chunks": 1,
        "done_chunks": 0,
        "error_code": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "heartbeat_at": heartbeat or now,
        "reserved_tokens": 1000,
        "estimated_tokens": 1000,
    }


class FakeProvider:
    async def complete(self, messages, max_output_tokens, json_mode=False):
        del messages, max_output_tokens, json_mode
        return CompletionResult("{}", 1, 1)


class JobsBackend:
    def __init__(self, *, owns_book: bool = True, rows: list[dict] | None = None):
        self.owns_book = owns_book
        self.rows = rows if rows is not None else [job("done")]
        self.calls: list[tuple[str, str, dict | None]] = []
        self.patches: list[dict] = []
        self.rpc_payload: dict | None = None

    async def request(self, method, path, *, params=None, json=None, **kwargs):
        del kwargs
        self.calls.append((method, path, params))
        if method == "GET" and path == "/rest/v1/books":
            if self.owns_book:
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": BOOK_ID,
                            "user_id": USER_ID,
                            "title": "Test book",
                            "author": None,
                            "page_count": 1,
                            "file_size_bytes": 20,
                            "needs_ocr": False,
                            "created_at": None,
                            "summary_json": None,
                            "sha256": "hash",
                            "storage_path": "private/file.pdf",
                        }
                    ],
                )
            return httpx.Response(200, json=[])
        if method == "GET" and path == "/rest/v1/book_pages":
            return httpx.Response(
                200, json=[{"page_number": 1, "text": "A source page."}]
            )
        if method == "POST" and path == "/rest/v1/rpc/create_generation_job":
            self.rpc_payload = json
            return httpx.Response(200, json=job())
        if method == "POST" and path == "/rest/v1/rpc/retry_generation_job":
            return httpx.Response(200, json=job())
        if method == "GET" and path == "/rest/v1/generation_jobs":
            rows = [
                row
                for row in self.rows
                if params and params.get("user_id") == f"eq.{row['user_id']}"
            ]
            if params and params.get("status") == "in.(queued,running)":
                rows = [row for row in rows if row["status"] in ("queued", "running")]
            return httpx.Response(200, json=rows)
        if method == "PATCH" and path == "/rest/v1/generation_jobs":
            self.patches.append(json)
            return httpx.Response(204)
        return httpx.Response(200, json=[])


def make_app(backend: JobsBackend):
    app = create_app()
    app.dependency_overrides[current_user_id] = lambda: USER_ID
    app.dependency_overrides[get_backend] = lambda: backend
    app.dependency_overrides[get_provider] = lambda: FakeProvider()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    return app


def test_map_job_requires_consent_before_creating_job() -> None:
    backend = JobsBackend()
    app = make_app(backend)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(
                f"/api/books/{BOOK_ID}/map-jobs", json={"consent": False}
            )

    response = asyncio.run(request())
    assert response.status_code == 400
    assert backend.rpc_payload is None


def test_map_job_queues_with_estimate_and_active_job_is_scoped() -> None:
    backend = JobsBackend()
    app = make_app(backend)

    async def requests():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                f"/api/books/{BOOK_ID}/map-jobs", json={"consent": True}
            )
            active = await client.get(f"/api/books/{BOOK_ID}/active-job")
        return created, active

    created, active = asyncio.run(requests())
    assert created.status_code == 202
    assert created.json()["id"] == JOB_ID
    assert backend.rpc_payload["p_kind"] == "map"
    assert backend.rpc_payload["p_estimated_tokens"] > 0
    assert backend.rpc_payload["p_consent_at"]
    assert active.status_code == 200
    assert all(
        params and params.get("user_id") == f"eq.{USER_ID}"
        for method, path, params in backend.calls
        if method == "GET" and path == "/rest/v1/generation_jobs"
    )


def test_cross_user_job_read_and_book_active_job_are_not_found() -> None:
    backend = JobsBackend(owns_book=False, rows=[job("running", owner=OTHER_ID)])
    app = make_app(backend)

    async def requests():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            create = await client.post(
                f"/api/books/{BOOK_ID}/map-jobs", json={"consent": True}
            )
            read = await client.get(f"/api/map-jobs/{JOB_ID}")
            active = await client.get(f"/api/books/{BOOK_ID}/active-job")
            retry = await client.post(f"/api/map-jobs/{JOB_ID}/retry")
        return create, read, active, retry

    create, read, active, retry = asyncio.run(requests())
    assert [
        create.status_code,
        read.status_code,
        active.status_code,
        retry.status_code,
    ] == [404, 404, 404, 404]
    assert all(
        params and params.get("user_id") == f"eq.{USER_ID}"
        for method, path, params in backend.calls
        if method == "GET" and path == "/rest/v1/generation_jobs"
    )


def test_stale_job_is_marked_failed_and_can_be_retried() -> None:
    old = (datetime.now(UTC) - timedelta(minutes=6)).isoformat()
    backend = JobsBackend(rows=[job("running", heartbeat=old)])
    app = make_app(backend)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(f"/api/map-jobs/{JOB_ID}")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "stale"
    assert any(patch.get("status") == "failed" for patch in backend.patches)


def test_stale_queued_job_is_marked_failed() -> None:
    old = (datetime.now(UTC) - timedelta(minutes=6)).isoformat()
    backend = JobsBackend(rows=[job("queued", heartbeat=old)])
    app = make_app(backend)

    async def request():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get(f"/api/map-jobs/{JOB_ID}")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert any(patch.get("error_code") == "stale" for patch in backend.patches)
