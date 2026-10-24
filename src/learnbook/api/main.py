"""Authenticated FastAPI service for hosted LearnBook documents."""

import asyncio
import hashlib
import logging
import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from learnbook.api.lessons import generate_topic_lesson
from learnbook.api.processing import extract_pdf_with_timeout
from learnbook.api.provider import GroqProvider, LLMProvider, ProviderError
from learnbook.api.schemas import (
    GenerationJob,
    HighlightInput,
    MapJobRequest,
    NoteInput,
    PreferencesInput,
    ProviderConsentRequest,
    StatusInput,
)
from learnbook.api.summary import _page_chunks, generate_book_summary
from learnbook.api.supabase_rest import SupabaseRest
from learnbook.config import Settings
from learnbook.core.ingestion.errors import FileTooLargeError, IngestionError
from learnbook.core.ingestion.models import DocumentSection
from learnbook.core.learning_path import (
    PathPreferences,
    TopicInput,
    build_learning_path,
)
from learnbook.core.understanding.digest import build_digest

logger = logging.getLogger(__name__)
_BUCKET = "book-pdfs"
_JOB_FAILURE_MESSAGE = (
    "The learning service could not complete this request. Please retry."
)
_STALE_JOB_MESSAGE = (
    "This generation paused unexpectedly. Retry to continue from saved work."
)
_BOOK_COLUMNS = (
    "id,title,author,page_count,file_size_bytes,needs_ocr,created_at,summary_json,"
    "sha256,storage_path,user_id"
)
_PUBLIC_BOOK_COLUMNS = (
    "id",
    "title",
    "author",
    "page_count",
    "file_size_bytes",
    "needs_ocr",
    "created_at",
    "summary_json",
)
_PROCESS_PROVIDER: GroqProvider | None = None
_PROCESS_PROVIDER_CONFIG: tuple[object, ...] | None = None


def digest_to_pages(digest_text: str) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in digest_text.splitlines():
        if line.startswith("## "):
            continue
        marker = re.fullmatch(r"\[p\.(\d+)\]", line)
        if marker:
            current = {"page_number": int(marker.group(1)), "text": ""}
            pages.append(current)
        elif current is not None:
            current["text"] = str(current["text"]) + line + " "
    return pages


def _public_book(book: dict[str, object], duplicate: bool = False) -> dict[str, object]:
    return {
        **{key: book.get(key) for key in _PUBLIC_BOOK_COLUMNS},
        "duplicate": duplicate,
    }


def get_settings() -> Settings:
    return Settings()


def get_backend(settings: Settings = Depends(get_settings)) -> SupabaseRest:
    return SupabaseRest(settings)


def get_allowed_emails(settings: Settings = Depends(get_settings)) -> list[str] | None:
    """Get allowed emails from env, return None if not set (no restriction)."""
    raw = getattr(settings, "allowed_emails", None)
    if raw:
        return [e.strip().lower() for e in raw.split(",") if e.strip()]
    return None


def get_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    global _PROCESS_PROVIDER, _PROCESS_PROVIDER_CONFIG
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
    signature = (
        key,
        settings.groq_model,
        settings.groq_tpm_limit,
        settings.groq_timeout_seconds,
    )
    if _PROCESS_PROVIDER is None or signature != _PROCESS_PROVIDER_CONFIG:
        _PROCESS_PROVIDER = GroqProvider(settings)
        _PROCESS_PROVIDER_CONFIG = signature
    return _PROCESS_PROVIDER


async def current_user_id(
    authorization: str | None = Header(default=None),
    backend: SupabaseRest = Depends(get_backend),
    allowed_emails: list[str] | None = Depends(get_allowed_emails),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    user_id = await backend.verify_user(token)

    # Check allowed emails if configured
    if allowed_emails is not None:
        # Get user email from Supabase
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(
                    f"{backend.base_url}/auth/v1/user",
                    headers={
                        "apikey": backend.anon_key,
                        "Authorization": f"Bearer {token}",
                    },
                )
                if resp.status_code == 200:
                    email = resp.json().get("email", "").lower()
                    if email not in allowed_emails:
                        raise HTTPException(
                            status_code=403,
                            detail="Access not allowed for this account.",
                        )
            except httpx.HTTPError:
                # If we can't verify email, deny access when restriction is enabled
                raise HTTPException(
                    status_code=403,
                    detail="Access not allowed for this account.",
                )

    return user_id


def create_app() -> FastAPI:
    settings = get_settings()
    allowed_origins = [
        origin.strip()
        for origin in settings.frontend_origins.split(",")
        if origin.strip()
    ]

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield

    app = FastAPI(title="LearnBook API", version="0.2.0", lifespan=lifespan)
    ingestion_slots = asyncio.Semaphore(settings.max_concurrent_ingestions)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    async def find_book(
        backend: SupabaseRest, user_id: str, book_id: uuid.UUID
    ) -> dict[str, object]:
        response = await backend.request(
            "GET",
            "/rest/v1/books",
            params={
                "id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": _BOOK_COLUMNS,
                "limit": "1",
            },
        )
        rows = response.json()
        if not rows:
            raise HTTPException(status_code=404, detail="Book not found.")
        return rows[0]

    async def find_topic(
        backend: SupabaseRest, user_id: str, book_id: uuid.UUID, topic_id: uuid.UUID
    ) -> dict[str, object]:
        response = await backend.request(
            "GET",
            "/rest/v1/topics",
            params={
                "id": f"eq.{topic_id}",
                "book_id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": "*",
                "limit": "1",
            },
        )
        rows = response.json()
        if not rows:
            raise HTTPException(status_code=404, detail="Topic not found.")
        return rows[0]

    async def find_topic_for_user(
        backend: SupabaseRest, user_id: str, topic_id: uuid.UUID
    ) -> dict[str, object]:
        response = await backend.request(
            "GET",
            "/rest/v1/topics",
            params={
                "id": f"eq.{topic_id}",
                "user_id": f"eq.{user_id}",
                "select": "*",
                "limit": "1",
            },
        )
        rows = response.json()
        if not rows:
            raise HTTPException(status_code=404, detail="Topic not found.")
        return rows[0]

    async def validate_topic_link(
        backend: SupabaseRest, user_id: str, book_id: uuid.UUID, topic_id: str | None
    ) -> None:
        if topic_id:
            try:
                parsed_id = uuid.UUID(topic_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=422, detail="Invalid topic id."
                ) from error
            await find_topic(backend, user_id, book_id, parsed_id)

    async def save_topic_tree(
        backend: SupabaseRest, user_id: str, book_id: uuid.UUID, nodes: list[object]
    ) -> None:
        await backend.request(
            "DELETE",
            "/rest/v1/topics",
            params={"book_id": f"eq.{book_id}", "user_id": f"eq.{user_id}"},
        )
        rows: list[dict[str, object]] = []

        def visit(node: object, parent_id: str | None) -> None:
            item = node.model_dump(mode="json", exclude={"children"})
            topic_id = str(uuid.uuid4())
            rows.append(
                {
                    "id": topic_id,
                    "book_id": str(book_id),
                    "user_id": user_id,
                    "parent_id": parent_id,
                    **item,
                }
            )
            for child in node.children:
                visit(child, topic_id)

        for node in nodes:
            visit(node, None)
        if rows:
            await backend.request(
                "POST", "/rest/v1/topics", json=rows, prefer="return=minimal"
            )

    async def set_job_fields(
        backend: SupabaseRest, job_id: str, **fields: object
    ) -> None:
        await backend.request(
            "PATCH",
            "/rest/v1/generation_jobs",
            params={"id": f"eq.{job_id}"},
            json={
                **fields,
                "updated_at": datetime.now(UTC).isoformat(),
                "heartbeat_at": datetime.now(UTC).isoformat(),
            },
            prefer="return=minimal",
        )

    async def run_map_job(
        job_id: str,
        user_id: str,
        book_id: str,
        backend: SupabaseRest,
        settings: Settings,
        provider: LLMProvider,
    ) -> None:
        try:
            job_rows = (
                await backend.request(
                    "GET",
                    "/rest/v1/generation_jobs",
                    params={
                        "id": f"eq.{job_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                        "limit": "1",
                    },
                )
            ).json()
            if not job_rows or job_rows[0]["status"] not in ("queued", "running"):
                return
            now = datetime.now(UTC)
            if job_rows[0]["status"] == "running":
                heartbeat = datetime.fromisoformat(
                    str(job_rows[0]["heartbeat_at"]).replace("Z", "+00:00")
                )
                if (now - heartbeat).total_seconds() < 300:
                    return
            await set_job_fields(
                backend,
                job_id,
                status="running",
                step="reading_source",
                error_code=None,
                error_message=None,
                heartbeat_at=now.isoformat(),
            )

            async def maintain_heartbeat() -> None:
                while True:
                    await asyncio.sleep(45)
                    current = (
                        await backend.request(
                            "GET",
                            "/rest/v1/generation_jobs",
                            params={
                                "id": f"eq.{job_id}",
                                "user_id": f"eq.{user_id}",
                                "select": "status",
                                "limit": "1",
                            },
                        )
                    ).json()
                    if not current or current[0].get("status") != "running":
                        return
                    await set_job_fields(backend, job_id)

            heartbeat_task = asyncio.create_task(maintain_heartbeat())
            book_rows = (
                await backend.request(
                    "GET",
                    "/rest/v1/books",
                    params={
                        "id": f"eq.{book_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "id,page_count,needs_ocr",
                        "limit": "1",
                    },
                )
            ).json()
            if not book_rows:
                raise ProviderError(
                    "provider_unavailable", "This book is no longer available."
                )
            if book_rows[0].get("needs_ocr"):
                raise ProviderError(
                    "needs_ocr",
                    "This PDF looks scanned, so its text cannot be read yet.",
                )
            page_rows = (
                await backend.request(
                    "GET",
                    "/rest/v1/book_pages",
                    params={
                        "book_id": f"eq.{book_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "page_number,text",
                        "order": "page_number.asc",
                    },
                )
            ).json()
            outline_rows = (
                await backend.request(
                    "GET",
                    "/rest/v1/book_outlines",
                    params={
                        "book_id": f"eq.{book_id}",
                        "user_id": f"eq.{user_id}",
                        "select": "sections,structure_source",
                        "limit": "1",
                    },
                )
            ).json()
            outline = outline_rows[0] if outline_rows else {}
            sections = [
                DocumentSection.model_validate(section)
                for section in outline.get("sections", [])
            ]
            structure_source = str(outline.get("structure_source", "fallback"))
            digest = build_digest(
                page_rows, sections=sections, structure_source=structure_source
            )
            await backend.request(
                "POST",
                "/rest/v1/daily_digests",
                params={"on_conflict": "book_id"},
                json={
                    "book_id": str(book_id),
                    "user_id": user_id,
                    "body": digest.text,
                    "structure_source": digest.structure_source,
                    "sections_total": digest.sections_total,
                    "sections_covered": digest.sections_covered,
                    "pages_covered": digest.pages_covered,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            max_chunk_chars = min(
                12_000, max(1200, int((settings.groq_max_request_tokens - 1700) * 3.5))
            )
            total_chunks = len(
                _page_chunks(digest_to_pages(digest.text), max_chunk_chars)
            )
            cached_rows = (
                await backend.request(
                    "GET",
                    "/rest/v1/job_chunk_results",
                    params={
                        "job_id": f"eq.{job_id}",
                        "select": "chunk_index,payload",
                        "order": "chunk_index.asc",
                    },
                )
            ).json()
            cached_chunks = {
                int(row["chunk_index"]): row["payload"] for row in cached_rows
            }
            await set_job_fields(
                backend,
                job_id,
                status="running",
                step="extracting_concepts",
                total_chunks=total_chunks,
                done_chunks=len(cached_chunks),
                progress_pct=min(
                    85, int(85 * len(cached_chunks) / max(total_chunks, 1))
                ),
            )

            async def record_usage(tokens_in: int, tokens_out: int) -> None:
                await backend.request(
                    "POST",
                    "/rest/v1/llm_usage_ledger",
                    json={
                        "user_id": user_id,
                        "job_id": job_id,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                    },
                    prefer="return=minimal",
                )
                await set_job_fields(backend, job_id, step="extracting_concepts")

            async def save_chunk(
                index: int,
                payload: dict[str, object],
                tokens_in: int,
                tokens_out: int,
                count: int,
            ) -> None:
                await backend.request(
                    "POST",
                    "/rest/v1/job_chunk_results",
                    params={"on_conflict": "job_id,chunk_index"},
                    json={
                        "job_id": job_id,
                        "chunk_index": index,
                        "payload": payload,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                    },
                    prefer="resolution=merge-duplicates,return=minimal",
                )
                done = index + 1
                await set_job_fields(
                    backend,
                    job_id,
                    step="extracting_concepts",
                    total_chunks=count,
                    done_chunks=done,
                    progress_pct=min(85, int(85 * done / max(count, 1))),
                )

            summary = await generate_book_summary(
                page_rows,
                provider,
                settings,
                cached_chunks=cached_chunks,
                on_chunk=save_chunk,
                on_usage=record_usage,
                sections=sections,
                structure_source=structure_source,
                digest_result=digest,
            )
            await backend.request(
                "PATCH",
                "/rest/v1/books",
                params={"id": f"eq.{book_id}", "user_id": f"eq.{user_id}"},
                json={"summary_json": summary.model_dump(mode="json")},
                prefer="return=minimal",
            )
            await set_job_fields(backend, job_id, step="merging_map", progress_pct=95)
            await save_topic_tree(backend, user_id, uuid.UUID(book_id), summary.topics)
            await set_job_fields(
                backend,
                job_id,
                status="done",
                step="complete",
                progress_pct=100,
                reserved_tokens=0,
                error_code=None,
                error_message=None,
            )
            logger.info(
                "generation job completed: id=%s chunks=%d", job_id, total_chunks
            )
        except ProviderError as error:
            await set_job_fields(
                backend,
                job_id,
                status="failed",
                step="failed",
                error_code=error.error_code,
                error_message=error.user_message,
                reserved_tokens=0,
            )
        except Exception:
            logger.error("generation job failed: id=%s", job_id)
            await set_job_fields(
                backend,
                job_id,
                status="failed",
                step="failed",
                error_code="provider_unavailable",
                error_message=_JOB_FAILURE_MESSAGE,
                reserved_tokens=0,
            )
        finally:
            if "heartbeat_task" in locals():
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    async def service_info() -> dict[str, str]:
        return {
            "service": "LearnBook API",
            "status": "ok",
            "health": "/health",
            "docs": "/docs",
        }

    @app.get("/api/books")
    async def list_books(
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        response = await backend.request(
            "GET",
            "/rest/v1/books",
            params={
                "user_id": f"eq.{user_id}",
                "select": _BOOK_COLUMNS,
                "order": "created_at.desc",
            },
        )
        return [_public_book(book) for book in response.json()]

    @app.post("/api/books", status_code=201)
    async def upload_book(
        file: UploadFile = File(...),
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
    ) -> dict[str, object]:
        file_bytes = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(file_bytes) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=FileTooLargeError.user_message,
            )
        if not file_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400, detail="This file is not a valid, readable PDF."
            )
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        duplicate_response = await backend.request(
            "GET",
            "/rest/v1/books",
            params={
                "user_id": f"eq.{user_id}",
                "sha256": f"eq.{file_hash}",
                "select": _BOOK_COLUMNS,
                "limit": "1",
            },
        )
        duplicates = duplicate_response.json()
        if duplicates:
            return _public_book(duplicates[0], duplicate=True)

        usage_response = await backend.request(
            "GET",
            "/rest/v1/books",
            params={
                "user_id": f"eq.{user_id}",
                "select": "id,file_size_bytes",
            },
        )
        user_books = usage_response.json()
        if len(user_books) >= settings.max_books_per_user:
            raise HTTPException(
                status_code=429,
                detail="Your library has reached its book limit.",
            )
        user_storage_bytes = sum(int(book["file_size_bytes"]) for book in user_books)
        max_user_storage = settings.max_user_storage_mb * 1024 * 1024
        if user_storage_bytes + len(file_bytes) > max_user_storage:
            raise HTTPException(
                status_code=413,
                detail="Your library has reached its storage limit.",
            )

        try:
            async with ingestion_slots:
                document = await run_in_threadpool(
                    extract_pdf_with_timeout,
                    file_bytes,
                    settings,
                    settings.pdf_processing_timeout_seconds,
                )
        except IngestionError as error:
            raise HTTPException(status_code=400, detail=error.user_message) from error
        if document.page_count > settings.public_max_pages:
            raise HTTPException(
                status_code=413,
                detail="This PDF exceeds the online page limit.",
            )
        extracted_chars = sum(page.char_count for page in document.pages)
        if extracted_chars > settings.max_extracted_chars:
            raise HTTPException(
                status_code=413,
                detail="This PDF exceeds the extracted-text storage limit.",
            )
        if not await backend.reserve_upload(user_id, settings):
            raise HTTPException(
                status_code=429,
                detail="Your daily upload limit has been reached.",
            )

        book_id = uuid.uuid4()
        storage_path = f"{user_id}/{book_id}.pdf"
        await backend.request(
            "POST",
            f"/storage/v1/object/{_BUCKET}/{storage_path}",
            content=file_bytes,
            content_type="application/pdf",
        )
        book_payload = {
            "id": str(book_id),
            "user_id": user_id,
            "title": document.title,
            "author": document.author,
            "page_count": document.page_count,
            "file_size_bytes": document.file_size_bytes,
            "needs_ocr": document.needs_ocr,
            "sha256": file_hash,
            "storage_path": storage_path,
            "summary_json": None,
        }
        try:
            await backend.request(
                "POST",
                "/rest/v1/books",
                json=book_payload,
                prefer="return=minimal",
            )
            page_rows = [
                {
                    "book_id": str(book_id),
                    "user_id": user_id,
                    "page_number": page.page_number,
                    "text": page.text,
                    "char_count": page.char_count,
                    "is_empty": page.is_empty,
                    "has_images": page.has_images,
                }
                for page in document.pages
            ]
            await backend.request(
                "POST",
                "/rest/v1/book_outlines",
                params={"on_conflict": "book_id"},
                json={
                    "book_id": str(book_id),
                    "user_id": user_id,
                    "sections": [
                        section.model_dump(mode="json") for section in document.sections
                    ],
                    "structure_source": document.structure_source,
                },
                prefer="resolution=merge-duplicates,return=minimal",
            )
            await backend.request(
                "POST",
                "/rest/v1/book_pages",
                json=page_rows,
                prefer="return=minimal",
            )
        except HTTPException:
            try:
                await backend.request(
                    "DELETE",
                    "/rest/v1/books",
                    params={
                        "id": f"eq.{book_id}",
                        "user_id": f"eq.{user_id}",
                    },
                )
            except HTTPException:
                pass
            try:
                await backend.request(
                    "DELETE",
                    f"/storage/v1/object/{_BUCKET}/{storage_path}",
                    allow_not_found=True,
                )
            except HTTPException:
                pass
            raise

        logger.info(
            "book stored: pages=%d bytes=%d sha256=%s",
            document.page_count,
            document.file_size_bytes,
            file_hash[:12],
        )
        return _public_book(book_payload)

    @app.get("/api/books/{book_id}/pages")
    async def get_book_pages(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        await find_book(backend, user_id, book_id)
        response = await backend.request(
            "GET",
            "/rest/v1/book_pages",
            params={
                "book_id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": "page_number,text,char_count,is_empty,has_images",
                "order": "page_number.asc",
            },
        )
        return response.json()

    @app.get("/api/books/{book_id}/pdf-url")
    async def get_pdf_url(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, str]:
        book = await find_book(backend, user_id, book_id)
        response = await backend.request(
            "POST",
            f"/storage/v1/object/sign/{_BUCKET}/{book['storage_path']}",
            json={"expiresIn": 300},
        )
        signed_path = response.json().get("signedURL")
        if not isinstance(signed_path, str):
            raise HTTPException(status_code=502, detail="Could not open this PDF.")
        signed_url = (
            signed_path
            if signed_path.startswith("http")
            else f"{backend.base_url}/storage/v1{signed_path}"
        )
        return {"url": signed_url}

    @app.get("/api/books/{book_id}/export", response_class=PlainTextResponse)
    async def export_book_text(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> str:
        await find_book(backend, user_id, book_id)
        response = await backend.request(
            "GET",
            "/rest/v1/book_pages",
            params={
                "book_id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": "page_number,text",
                "order": "page_number.asc",
            },
        )
        return "\n\n".join(
            f"=== Page {row['page_number']} ===\n{row['text']}"
            for row in response.json()
        )

    async def stale_if_needed(
        backend: SupabaseRest, job: dict[str, object]
    ) -> dict[str, object]:
        if job.get("status") not in ("queued", "running"):
            return job
        heartbeat = datetime.fromisoformat(
            str(job["heartbeat_at"]).replace("Z", "+00:00")
        )
        if (datetime.now(UTC) - heartbeat).total_seconds() <= 300:
            return job
        await set_job_fields(
            backend,
            str(job["id"]),
            status="failed",
            step="failed",
            error_code="stale",
            error_message=_STALE_JOB_MESSAGE,
            reserved_tokens=0,
        )
        return {
            **job,
            "status": "failed",
            "step": "failed",
            "error_code": "stale",
            "error_message": _STALE_JOB_MESSAGE,
            "reserved_tokens": 0,
        }

    async def read_job_for_user(
        backend: SupabaseRest, user_id: str, job_id: uuid.UUID
    ) -> dict[str, object]:
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/generation_jobs",
                params={
                    "id": f"eq.{job_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=404, detail="Generation job not found.")
        return await stale_if_needed(backend, rows[0])

    def estimate_map_tokens(
        pages: list[dict[str, object]], settings: Settings
    ) -> tuple[int, int]:
        maximum_chars = min(
            12_000, max(1200, int((settings.groq_max_request_tokens - 1700) * 3.5))
        )
        chunks = len(_page_chunks(pages, maximum_chars))
        source_chars = sum(len(str(page.get("text", ""))) for page in pages)
        estimated = int(source_chars / 3.5 + 0.999) + chunks * 2400 + 3000
        return chunks, estimated

    @app.post("/api/books/{book_id}/map-jobs", status_code=202)
    async def create_map_job(
        request: MapJobRequest,
        book_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
        provider: LLMProvider = Depends(get_provider),
    ) -> dict[str, object]:
        if request.consent is not True:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Consent is required before sending book text "
                    "to the learning provider."
                ),
            )
        book = await find_book(backend, user_id, book_id)
        if book.get("needs_ocr"):
            raise HTTPException(
                status_code=422,
                detail="This PDF looks scanned, so its text cannot be read yet.",
            )
        page_response = await backend.request(
            "GET",
            "/rest/v1/book_pages",
            params={
                "book_id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": "page_number,text",
                "order": "page_number.asc",
            },
        )
        pages = page_response.json()
        if not pages:
            raise HTTPException(
                status_code=422, detail="This book has no readable source text."
            )
        total_chars = sum(len(str(page.get("text", ""))) for page in pages)
        if total_chars > settings.ai_max_book_chars:
            raise HTTPException(
                status_code=413,
                detail="This book exceeds the learning-service size limit.",
            )
        chunk_count, estimated_tokens = estimate_map_tokens(pages, settings)
        try:
            response = await backend.request(
                "POST",
                "/rest/v1/rpc/create_generation_job",
                json={
                    "p_user_id": user_id,
                    "p_book_id": str(book_id),
                    "p_kind": "map",
                    "p_estimated_tokens": estimated_tokens,
                    "p_daily_token_budget": settings.groq_daily_token_budget,
                    "p_max_books_per_day": settings.max_books_per_user_per_day,
                    "p_max_lessons_per_day": settings.max_lessons_per_user_per_day,
                    "p_consent_at": datetime.now(UTC).isoformat(),
                },
            )
        except HTTPException as error:
            if (
                error.status_code == 502
                and estimated_tokens > settings.groq_daily_token_budget
            ):
                raise HTTPException(
                    status_code=429,
                    detail="Daily capacity reached. Please try again tomorrow.",
                ) from error
            raise
        job = response.json()
        if isinstance(job, list):
            job = job[0] if job else None
        if not isinstance(job, dict):
            raise HTTPException(
                status_code=502, detail="Could not queue this learning job."
            )
        await set_job_fields(backend, str(job["id"]), total_chunks=chunk_count)
        job["total_chunks"] = chunk_count
        background_tasks.add_task(
            run_map_job,
            str(job["id"]),
            user_id,
            str(book_id),
            backend,
            settings,
            provider,
        )
        return GenerationJob.model_validate(job).model_dump(mode="json")

    @app.get("/api/map-jobs/{job_id}")
    async def get_map_job(
        job_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        job = await read_job_for_user(backend, user_id, job_id)
        return GenerationJob.model_validate(job).model_dump(mode="json")

    @app.get("/api/books/{book_id}/active-job")
    async def get_active_map_job(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object] | None:
        await find_book(backend, user_id, book_id)
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/generation_jobs",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "kind": "eq.map",
                    "status": "in.(queued,running)",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            return None
        job = await stale_if_needed(backend, rows[0])
        return GenerationJob.model_validate(job).model_dump(mode="json")

    @app.post("/api/map-jobs/{job_id}/retry", status_code=202)
    async def retry_map_job(
        job_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
        provider: LLMProvider = Depends(get_provider),
    ) -> dict[str, object]:
        job = await read_job_for_user(backend, user_id, job_id)
        if job["status"] != "failed":
            raise HTTPException(
                status_code=409, detail="This generation job cannot be retried yet."
            )
        response = await backend.request(
            "POST",
            "/rest/v1/rpc/retry_generation_job",
            json={
                "p_job_id": str(job_id),
                "p_user_id": user_id,
                "p_daily_token_budget": settings.groq_daily_token_budget,
            },
        )
        updated = response.json()
        if isinstance(updated, list):
            updated = updated[0] if updated else None
        if not isinstance(updated, dict):
            raise HTTPException(
                status_code=502, detail="Could not retry this generation job."
            )
        background_tasks.add_task(
            run_map_job,
            str(job_id),
            user_id,
            str(updated["book_id"]),
            backend,
            settings,
            provider,
        )
        return GenerationJob.model_validate(updated).model_dump(mode="json")

    @app.get("/api/books/{book_id}/map")
    async def get_book_map(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        book = await find_book(backend, user_id, book_id)
        topics = (
            await backend.request(
                "GET",
                "/rest/v1/topics",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "order": "position.asc",
                },
            )
        ).json()
        progress = (
            await backend.request(
                "GET",
                "/rest/v1/topic_progress",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "topic_id,status,updated_at",
                },
            )
        ).json()
        progress_by_id = {row["topic_id"]: row for row in progress}
        for topic in topics:
            topic["progress"] = progress_by_id.get(topic["id"], {"status": "new"})
            topic["children"] = []
        by_id = {topic["id"]: topic for topic in topics}
        roots = []
        for topic in topics:
            parent_id = topic.get("parent_id")
            if parent_id in by_id:
                by_id[parent_id]["children"].append(topic)
            else:
                roots.append(topic)
        return {
            "book_id": str(book_id),
            "topics": roots,
            "summary": book.get("summary_json"),
        }

    @app.put("/api/books/{book_id}/preferences")
    async def put_preferences(
        body: PreferencesInput,
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        if not 5 <= body.daily_minutes <= 180:
            raise HTTPException(
                status_code=422, detail="Daily minutes must be between 5 and 180."
            )
        await find_book(backend, user_id, book_id)
        payload = {
            "user_id": user_id,
            "book_id": str(book_id),
            **body.model_dump(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        response = await backend.request(
            "POST",
            "/rest/v1/learning_preferences",
            params={"on_conflict": "user_id,book_id"},
            json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return response.json()[0] if response.json() else payload

    @app.get("/api/books/{book_id}/preferences")
    async def get_preferences(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_book(backend, user_id, book_id)
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/learning_preferences",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(
                status_code=404, detail="Learning preferences not found."
            )
        return rows[0]

    @app.post("/api/books/{book_id}/path")
    async def build_path(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_book(backend, user_id, book_id)
        prefs_response = await backend.request(
            "GET",
            "/rest/v1/learning_preferences",
            params={
                "book_id": f"eq.{book_id}",
                "user_id": f"eq.{user_id}",
                "select": "*",
                "limit": "1",
            },
        )
        if not prefs_response.json():
            raise HTTPException(
                status_code=400, detail="Save learning preferences first."
            )
        prefs = prefs_response.json()[0]
        topic_rows = (
            await backend.request(
                "GET",
                "/rest/v1/topics",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "id,parent_id,importance,est_minutes,position",
                    "order": "position.asc",
                },
            )
        ).json()
        completed_rows = (
            await backend.request(
                "GET",
                "/rest/v1/path_items",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": (
                        "topic_id,position,day_number,is_optional,"
                        "minutes_allocated,is_condensed,completed_at"
                    ),
                    "completed_at": "not.is.null",
                },
            )
        ).json()
        items = build_learning_path(
            [TopicInput(**row) for row in topic_rows],
            PathPreferences(
                int(prefs["daily_minutes"]),
                frozenset(row["topic_id"] for row in completed_rows),
            ),
        )
        await backend.request(
            "DELETE",
            "/rest/v1/learning_paths",
            params={"book_id": f"eq.{book_id}", "user_id": f"eq.{user_id}"},
        )
        path_response = await backend.request(
            "POST",
            "/rest/v1/learning_paths",
            json={
                "user_id": user_id,
                "book_id": str(book_id),
                "goal": prefs["goal"],
                "minutes_per_topic": prefs["minutes_per_topic"],
                "daily_minutes": prefs["daily_minutes"],
            },
            prefer="return=representation",
        )
        path_rows = path_response.json()
        if not path_rows:
            raise HTTPException(
                status_code=502, detail="Could not save the learning path."
            )
        path = path_rows[0]
        completed_item_rows = [
            {
                "path_id": path["id"],
                "user_id": user_id,
                "book_id": str(book_id),
                "topic_id": row["topic_id"],
                "position": int(row["position"]),
                "day_number": int(row["day_number"]),
                "is_optional": bool(row["is_optional"]),
                "minutes_allocated": int(row["minutes_allocated"]),
                "is_condensed": bool(row["is_condensed"]),
                "completed_at": row["completed_at"],
            }
            for row in completed_rows
        ]
        position_offset = (
            max((int(row["position"]) for row in completed_item_rows), default=-1) + 1
        )
        new_item_rows = [
            {
                "path_id": path["id"],
                "user_id": user_id,
                "book_id": str(book_id),
                "minutes_allocated": item.minutes_allocated,
                "is_condensed": item.is_condensed,
                **item.__dict__,
                "position": item.position + position_offset,
            }
            for item in items
        ]
        item_rows = [*completed_item_rows, *new_item_rows]
        if item_rows:
            await backend.request(
                "POST", "/rest/v1/path_items", json=item_rows, prefer="return=minimal"
            )
        return {"path": path, "items": item_rows}

    @app.get("/api/books/{book_id}/path")
    async def get_path(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_book(backend, user_id, book_id)
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/learning_paths",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=404, detail="Learning path not found.")
        path = rows[0]
        items = (
            await backend.request(
                "GET",
                "/rest/v1/path_items",
                params={
                    "path_id": f"eq.{path['id']}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "order": "position.asc",
                },
            )
        ).json()
        by_day: dict[int, list[dict[str, object]]] = {}
        for item in items:
            by_day.setdefault(int(item["day_number"]), []).append(item)
        daily = [
            {
                "day_number": day,
                "minutes": sum(
                    int(item.get("minutes_allocated", 0)) for item in day_items
                ),
                "items": day_items,
            }
            for day, day_items in sorted(by_day.items())
        ]
        return {"path": path, "days": daily, "items": items}

    @app.post("/api/path-items/{item_id}/complete")
    async def complete_path_item(
        item_id: uuid.UUID,
        body: StatusInput,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        if body.status not in {"understood", "review"}:
            raise HTTPException(status_code=422, detail="Choose understood or review.")
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/path_items",
                params={
                    "id": f"eq.{item_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "id,topic_id,book_id",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=404, detail="Path item not found.")
        item = rows[0]
        completed_at = datetime.now(UTC).isoformat()
        await backend.request(
            "PATCH",
            "/rest/v1/path_items",
            params={"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"},
            json={"completed_at": completed_at},
            prefer="return=minimal",
        )
        progress = await backend.request(
            "POST",
            "/rest/v1/topic_progress",
            params={"on_conflict": "user_id,topic_id"},
            json={
                "user_id": user_id,
                "book_id": item["book_id"],
                "topic_id": item["topic_id"],
                "status": body.status,
                "updated_at": completed_at,
            },
            prefer="resolution=merge-duplicates,return=representation",
        )
        return progress.json()[0] if progress.json() else {"status": body.status}

    @app.get("/api/books/{book_id}/progress")
    async def get_progress(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_book(backend, user_id, book_id)
        topics = (
            await backend.request(
                "GET",
                "/rest/v1/topics",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "id,importance,title",
                },
            )
        ).json()
        progress = (
            await backend.request(
                "GET",
                "/rest/v1/topic_progress",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "topic_id,status,updated_at",
                },
            )
        ).json()
        items = (
            await backend.request(
                "GET",
                "/rest/v1/path_items",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": (
                        "topic_id,day_number,is_optional,minutes_allocated,completed_at"
                    ),
                    "order": "position.asc",
                },
            )
        ).json()
        status_by_id = {row["topic_id"]: row["status"] for row in progress}
        core = [topic for topic in topics if int(topic["importance"]) >= 4]
        core_understood = sum(
            status_by_id.get(topic["id"], "new") == "understood" for topic in core
        )
        required = [item for item in items if not item["is_optional"]]
        total_minutes = sum(int(item.get("minutes_allocated", 0)) for item in required)
        completed_minutes = sum(
            int(item.get("minutes_allocated", 0))
            for item in required
            if item.get("completed_at")
            and status_by_id.get(item["topic_id"]) in {"understood", "review"}
        )
        days = {int(item["day_number"]) for item in items}
        current_day = min(
            (
                int(item["day_number"])
                for item in required
                if not item.get("completed_at")
            ),
            default=max(days, default=0),
        )
        return {
            "path_percent": round(100 * completed_minutes / total_minutes)
            if total_minutes
            else 0,
            "core_percent": round(100 * core_understood / len(core)) if core else 0,
            "topics_total": len(topics),
            "topics_understood": sum(
                status == "understood" for status in status_by_id.values()
            ),
            "days_total": len(days),
            "current_day": current_day,
            "topics": [
                {**topic, "status": status_by_id.get(topic["id"], "new")}
                for topic in topics
            ],
        }

    @app.get("/api/shelf")
    async def get_shelf(
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        books = (
            await backend.request(
                "GET",
                "/rest/v1/books",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": _PUBLIC_BOOK_COLUMNS,
                    "order": "created_at.desc",
                },
            )
        ).json()
        shelf = []
        for book in books:
            progress = await get_progress(uuid.UUID(str(book["id"])), user_id, backend)
            try:
                path = await get_path(uuid.UUID(str(book["id"])), user_id, backend)
            except HTTPException as error:
                if error.status_code != 404:
                    raise
                path = {"items": []}
            next_item = next(
                (
                    item
                    for item in path["items"]
                    if not item.get("completed_at") and not item.get("is_optional")
                ),
                None,
            )
            shelf.append(
                {
                    "id": book["id"],
                    "title": book.get("title"),
                    "path_percent": progress["path_percent"],
                    "core_percent": progress["core_percent"],
                    "topics_understood": progress["topics_understood"],
                    "topics_total": progress["topics_total"],
                    "next_day": next_item.get("day_number") if next_item else None,
                    "next_minutes": next_item.get("minutes_allocated")
                    if next_item
                    else 0,
                    "last_activity": max(
                        (
                            row.get("updated_at")
                            for row in progress["topics"]
                            if row.get("updated_at")
                        ),
                        default=book.get("created_at"),
                    ),
                }
            )
        return shelf

    @app.get("/api/books/{book_id}/learned")
    async def get_learned(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        await find_book(backend, user_id, book_id)
        completed = (
            await backend.request(
                "GET",
                "/rest/v1/path_items",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "completed_at": "not.is.null",
                    "select": "topic_id,completed_at",
                },
            )
        ).json()
        result = []
        for item in completed:
            topic = await find_topic_for_user(
                backend, user_id, uuid.UUID(item["topic_id"])
            )
            lessons = (
                await backend.request(
                    "GET",
                    "/rest/v1/lessons",
                    params={
                        "topic_id": f"eq.{item['topic_id']}",
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                    },
                )
            ).json()
            notes = (
                await backend.request(
                    "GET",
                    "/rest/v1/notes",
                    params={
                        "topic_id": f"eq.{item['topic_id']}",
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                    },
                )
            ).json()
            passages = (
                await backend.request(
                    "GET",
                    "/rest/v1/highlights",
                    params={
                        "topic_id": f"eq.{item['topic_id']}",
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                    },
                )
            ).json()
            result.append(
                {
                    "topic": topic,
                    "completed_at": item["completed_at"],
                    "lesson": lessons[0] if lessons else None,
                    "notes": notes,
                    "passages": passages,
                }
            )
        return result

    @app.put("/api/topics/{topic_id}/status")
    async def put_topic_status(
        body: StatusInput,
        topic_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        response = await backend.request(
            "GET",
            "/rest/v1/topics",
            params={
                "id": f"eq.{topic_id}",
                "user_id": f"eq.{user_id}",
                "select": "id,book_id",
                "limit": "1",
            },
        )
        if not response.json():
            raise HTTPException(status_code=404, detail="Topic not found.")
        topic_row = response.json()[0]
        payload = {
            "topic_id": str(topic_id),
            "book_id": topic_row["book_id"],
            "user_id": user_id,
            **body.model_dump(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = await backend.request(
            "POST",
            "/rest/v1/topic_progress",
            params={"on_conflict": "user_id,topic_id"},
            json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return result.json()[0] if result.json() else payload

    @app.get("/api/topics/{topic_id}/lesson")
    async def get_topic_lesson(
        topic_id: uuid.UUID,
        target_minutes: int = Query(default=10, ge=5, le=10),
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        if target_minutes not in {5, 10}:
            raise HTTPException(
                status_code=422,
                detail="Lesson target must be five or ten minutes.",
            )
        await find_topic_for_user(backend, user_id, topic_id)
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/lessons",
                params={
                    "topic_id": f"eq.{topic_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "target_minutes": f"eq.{target_minutes}",
                    "order": "created_at.desc",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=404, detail="Lesson not found.")
        return rows[0]

    async def run_lesson_job(
        job_id: str,
        user_id: str,
        topic_id: uuid.UUID,
        target_minutes: int,
        backend: SupabaseRest,
        settings: Settings,
        provider: LLMProvider,
    ) -> None:
        await set_job_fields(
            backend,
            job_id,
            status="running",
            step="generating_lesson",
            progress_pct=10,
        )
        try:
            await create_topic_lesson(
                ProviderConsentRequest(consent=True, target_minutes=target_minutes),
                topic_id,
                user_id,
                backend,
                settings,
                provider,
            )
            await set_job_fields(
                backend,
                job_id,
                status="done",
                step="complete",
                progress_pct=100,
                reserved_tokens=0,
            )
        except Exception:
            logger.error("lesson job failed: id=%s", job_id)
            await set_job_fields(
                backend,
                job_id,
                status="failed",
                step="failed",
                error_code="provider_unavailable",
                error_message=_JOB_FAILURE_MESSAGE,
                reserved_tokens=0,
            )

    @app.post("/api/topics/{topic_id}/lesson-jobs", status_code=202)
    async def create_topic_lesson_job(
        request: ProviderConsentRequest,
        topic_id: uuid.UUID,
        background_tasks: BackgroundTasks,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
        provider: LLMProvider = Depends(get_provider),
    ) -> dict[str, object]:
        if not request.consent:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Confirm the provider data-use notice before generating a lesson."
                ),
            )
        topic = await find_topic_for_user(backend, user_id, topic_id)
        existing = (
            await backend.request(
                "GET",
                "/rest/v1/lessons",
                params={
                    "topic_id": f"eq.{topic_id}",
                    "user_id": f"eq.{user_id}",
                    "target_minutes": f"eq.{request.target_minutes}",
                    "select": "*",
                    "limit": "1",
                },
            )
        ).json()
        if existing:
            return {"cached": existing[0]}
        estimated = min(
            settings.groq_max_request_tokens,
            2200 + len(str(topic.get("summary", ""))) // 3,
        )
        response = await backend.request(
            "POST",
            "/rest/v1/rpc/create_generation_job",
            json={
                "p_user_id": user_id,
                "p_book_id": topic["book_id"],
                "p_kind": "lesson",
                "p_estimated_tokens": estimated,
                "p_daily_token_budget": settings.groq_daily_token_budget,
                "p_max_books_per_day": settings.max_books_per_user_per_day,
                "p_max_lessons_per_day": settings.max_lessons_per_user_per_day,
                "p_consent_at": datetime.now(UTC).isoformat(),
            },
        )
        row = response.json()
        if isinstance(row, list):
            row = row[0] if row else None
        if not isinstance(row, dict):
            raise HTTPException(status_code=502, detail="Could not queue this lesson.")
        job_id = str(row["id"])
        await backend.request(
            "PATCH",
            "/rest/v1/generation_jobs",
            params={"id": f"eq.{job_id}", "user_id": f"eq.{user_id}"},
            json={"topic_id": str(topic_id)},
            prefer="return=minimal",
        )
        row.update(
            {
                "topic_id": str(topic_id),
                "total_chunks": 1,
                "done_chunks": 0,
                "step": "queued",
            }
        )
        background_tasks.add_task(
            run_lesson_job,
            job_id,
            user_id,
            topic_id,
            request.target_minutes,
            backend,
            settings,
            provider,
        )
        return GenerationJob.model_validate(row).model_dump(mode="json")

    @app.get("/api/topics/{topic_id}/lesson-jobs/{job_id}")
    async def get_topic_lesson_job(
        topic_id: uuid.UUID,
        job_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_topic_for_user(backend, user_id, topic_id)
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/generation_jobs",
                params={
                    "id": f"eq.{job_id}",
                    "topic_id": f"eq.{topic_id}",
                    "user_id": f"eq.{user_id}",
                    "kind": "eq.lesson",
                    "select": "*",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=404, detail="Lesson job not found.")
        return GenerationJob.model_validate(rows[0]).model_dump(mode="json")

    @app.post("/api/topics/{topic_id}/lesson")
    async def create_topic_lesson(
        request: ProviderConsentRequest,
        topic_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
        provider: LLMProvider = Depends(get_provider),
    ) -> dict[str, object]:
        topic = await find_topic_for_user(backend, user_id, topic_id)
        existing = (
            await backend.request(
                "GET",
                "/rest/v1/lessons",
                params={
                    "topic_id": f"eq.{topic_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "target_minutes": f"eq.{request.target_minutes}",
                    "limit": "1",
                },
            )
        ).json()
        if existing:
            return existing[0]
        if not request.consent:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Confirm the provider data-use notice before generating a lesson."
                ),
            )
        if not await backend.reserve_summary(user_id, settings):
            raise HTTPException(
                status_code=429,
                detail="Your AI lesson limit has been reached. Try again later.",
            )

        book_rows = (
            await backend.request(
                "GET",
                "/rest/v1/books",
                params={
                    "id": f"eq.{topic['book_id']}",
                    "user_id": f"eq.{user_id}",
                    "select": "id,page_count",
                    "limit": "1",
                },
            )
        ).json()
        if not book_rows:
            raise HTTPException(status_code=404, detail="Book not found.")
        page_count = int(book_rows[0]["page_count"])
        referenced_pages = sorted(set(int(page) for page in topic["page_refs"]))
        selected_pages = sorted(
            {
                page
                for reference in referenced_pages
                for page in (reference - 1, reference, reference + 1)
                if 1 <= page <= page_count
            }
        )
        if not selected_pages:
            raise HTTPException(
                status_code=422, detail="This topic has no source pages."
            )
        page_rows = (
            await backend.request(
                "GET",
                "/rest/v1/book_pages",
                params={
                    "book_id": f"eq.{topic['book_id']}",
                    "user_id": f"eq.{user_id}",
                    "page_number": f"in.({','.join(map(str, selected_pages))})",
                    "select": "page_number,text",
                    "order": "page_number.asc",
                },
            )
        ).json()
        if not page_rows:
            raise HTTPException(status_code=422, detail="Source pages are unavailable.")

        async def record_lesson_usage(tokens_in: int, tokens_out: int) -> None:
            await backend.request(
                "POST",
                "/rest/v1/llm_usage_ledger",
                json={
                    "user_id": user_id,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                },
                prefer="return=minimal",
            )

        try:
            lesson = await generate_topic_lesson(
                title=str(topic["title"]),
                summary=str(topic["summary"]),
                page_refs=referenced_pages,
                pages=page_rows,
                provider=provider,
                settings=settings,
                target_minutes=request.target_minutes,
                on_usage=record_lesson_usage,
            )
        except ProviderError as error:
            status_code = (
                429
                if error.error_code
                in {"rate_limited", "budget_exhausted", "quota_exceeded"}
                else 502
            )
            raise HTTPException(
                status_code=status_code, detail=error.user_message
            ) from error
        payload = {
            "user_id": user_id,
            "topic_id": str(topic_id),
            "book_id": str(topic["book_id"]),
            **lesson.model_dump(mode="json"),
            "target_minutes": request.target_minutes,
        }
        response = await backend.request(
            "POST",
            "/rest/v1/lessons",
            params={"on_conflict": "user_id,topic_id,target_minutes"},
            json=payload,
            prefer="resolution=ignore-duplicates,return=representation",
        )
        saved = response.json()
        if saved:
            return saved[0]
        # A concurrent request may have inserted this topic's lesson first.
        rows = (
            await backend.request(
                "GET",
                "/rest/v1/lessons",
                params={
                    "topic_id": f"eq.{topic_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "limit": "1",
                },
            )
        ).json()
        if not rows:
            raise HTTPException(status_code=502, detail="Could not save the lesson.")
        return rows[0]

    @app.post("/api/books/{book_id}/highlights", status_code=201)
    async def create_highlight(
        body: HighlightInput,
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        book = await find_book(backend, user_id, book_id)
        if body.page > int(book["page_count"]):
            raise HTTPException(status_code=422, detail="Page is outside this book.")
        await validate_topic_link(backend, user_id, book_id, body.topic_id)
        payload = {"user_id": user_id, "book_id": str(book_id), **body.model_dump()}
        response = await backend.request(
            "POST", "/rest/v1/highlights", json=payload, prefer="return=representation"
        )
        return response.json()[0] if response.json() else payload

    @app.get("/api/books/{book_id}/highlights")
    async def list_highlights(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        await find_book(backend, user_id, book_id)
        return (
            await backend.request(
                "GET",
                "/rest/v1/highlights",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "order": "created_at.desc",
                },
            )
        ).json()

    @app.delete("/api/highlights/{highlight_id}", status_code=204)
    async def delete_highlight(
        highlight_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> None:
        existing = (
            await backend.request(
                "GET",
                "/rest/v1/highlights",
                params={
                    "id": f"eq.{highlight_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "id",
                    "limit": "1",
                },
            )
        ).json()
        if not existing:
            raise HTTPException(status_code=404, detail="Highlight not found.")
        await backend.request(
            "DELETE",
            "/rest/v1/highlights",
            params={"id": f"eq.{highlight_id}", "user_id": f"eq.{user_id}"},
        )

    @app.post("/api/books/{book_id}/notes", status_code=201)
    async def create_note(
        body: NoteInput,
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        await find_book(backend, user_id, book_id)
        await validate_topic_link(backend, user_id, book_id, body.topic_id)
        payload = {"user_id": user_id, "book_id": str(book_id), **body.model_dump()}
        response = await backend.request(
            "POST", "/rest/v1/notes", json=payload, prefer="return=representation"
        )
        return response.json()[0] if response.json() else payload

    @app.get("/api/books/{book_id}/notes")
    async def list_notes(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> list[dict[str, object]]:
        await find_book(backend, user_id, book_id)
        return (
            await backend.request(
                "GET",
                "/rest/v1/notes",
                params={
                    "book_id": f"eq.{book_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "*",
                    "order": "updated_at.desc",
                },
            )
        ).json()

    @app.put("/api/notes/{note_id}")
    async def update_note(
        body: NoteInput,
        note_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
        existing = (
            await backend.request(
                "GET",
                "/rest/v1/notes",
                params={
                    "id": f"eq.{note_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "book_id",
                    "limit": "1",
                },
            )
        ).json()
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found.")
        book_id = uuid.UUID(existing[0]["book_id"])
        await validate_topic_link(backend, user_id, book_id, body.topic_id)
        payload = body.model_dump() | {"updated_at": datetime.now(UTC).isoformat()}
        response = await backend.request(
            "PATCH",
            "/rest/v1/notes",
            params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
            json=payload,
            prefer="return=representation",
        )
        return response.json()[0] if response.json() else payload

    @app.delete("/api/notes/{note_id}", status_code=204)
    async def delete_note(
        note_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> None:
        existing = (
            await backend.request(
                "GET",
                "/rest/v1/notes",
                params={
                    "id": f"eq.{note_id}",
                    "user_id": f"eq.{user_id}",
                    "select": "id",
                    "limit": "1",
                },
            )
        ).json()
        if not existing:
            raise HTTPException(status_code=404, detail="Note not found.")
        await backend.request(
            "DELETE",
            "/rest/v1/notes",
            params={"id": f"eq.{note_id}", "user_id": f"eq.{user_id}"},
        )

    @app.delete("/api/books/{book_id}", status_code=204)
    async def delete_book(
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> None:
        book = await find_book(backend, user_id, book_id)
        await backend.request(
            "DELETE",
            f"/storage/v1/object/{_BUCKET}/{book['storage_path']}",
            allow_not_found=True,
        )
        await backend.request(
            "DELETE",
            "/rest/v1/books",
            params={"id": f"eq.{book_id}", "user_id": f"eq.{user_id}"},
        )

    @app.delete("/api/books", status_code=204)
    async def delete_library(
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> None:
        response = await backend.request(
            "GET",
            "/rest/v1/books",
            params={
                "user_id": f"eq.{user_id}",
                "select": "storage_path",
            },
        )
        for book in response.json():
            await backend.request(
                "DELETE",
                f"/storage/v1/object/{_BUCKET}/{book['storage_path']}",
                allow_not_found=True,
            )
        await backend.request(
            "DELETE",
            "/rest/v1/books",
            params={"user_id": f"eq.{user_id}"},
        )

    return app


app = create_app()
