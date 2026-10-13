"""Authenticated FastAPI service for hosted LearnBook documents."""

import asyncio
import hashlib
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from learnbook.api.processing import extract_pdf_with_timeout
from learnbook.api.schemas import (
    GenerateSummaryRequest,
    HighlightInput,
    NoteInput,
    PreferencesInput,
    StatusInput,
)
from learnbook.api.summary import generate_book_summary
from learnbook.api.supabase_rest import SupabaseRest
from learnbook.config import Settings
from learnbook.core.ingestion.errors import FileTooLargeError, IngestionError
from learnbook.core.learning_path import (
    PathPreferences,
    TopicInput,
    build_learning_path,
)

logger = logging.getLogger(__name__)
_BUCKET = "book-pdfs"
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


def _public_book(book: dict[str, object], duplicate: bool = False) -> dict[str, object]:
    return {
        **{key: book.get(key) for key in _PUBLIC_BOOK_COLUMNS},
        "duplicate": duplicate,
    }


def get_settings() -> Settings:
    return Settings()


def get_backend(settings: Settings = Depends(get_settings)) -> SupabaseRest:
    return SupabaseRest(settings)


async def current_user_id(
    authorization: str | None = Header(default=None),
    backend: SupabaseRest = Depends(get_backend),
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return await backend.verify_user(token)


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
        allow_headers=["Authorization", "Content-Type", "X-Gemini-Api-Key"],
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

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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

    @app.post("/api/books/{book_id}/summary")
    async def make_summary(
        request: GenerateSummaryRequest,
        book_id: uuid.UUID,
        x_gemini_api_key: str = Header(default=""),
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
        settings: Settings = Depends(get_settings),
    ) -> dict[str, object]:
        if not request.data_use_consent:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Confirm the provider data-use notice before generating a guide."
                ),
            )
        if len(x_gemini_api_key) < 20:
            raise HTTPException(status_code=400, detail="Enter a valid Gemini API key.")
        await find_book(backend, user_id, book_id)
        allowed = await backend.reserve_summary(user_id, settings)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Your summary limit has been reached. Try again later.",
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
        summary = await generate_book_summary(
            page_response.json(),
            x_gemini_api_key,
            settings,
        )
        await backend.request(
            "PATCH",
            "/rest/v1/books",
            params={"id": f"eq.{book_id}", "user_id": f"eq.{user_id}"},
            json={"summary_json": summary.model_dump(mode="json")},
            prefer="return=minimal",
        )
        await save_topic_tree(backend, user_id, book_id, summary.topics)
        return {"book_id": str(book_id), "summary": summary.model_dump(mode="json")}

    @app.get("/api/books/{book_id}/map")
    async def get_book_map(
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
        return {"book_id": str(book_id), "topics": roots}

    @app.put("/api/books/{book_id}/preferences")
    async def put_preferences(
        body: PreferencesInput,
        book_id: uuid.UUID,
        user_id: str = Depends(current_user_id),
        backend: SupabaseRest = Depends(get_backend),
    ) -> dict[str, object]:
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
        items = build_learning_path(
            [TopicInput(**row) for row in topic_rows],
            PathPreferences(prefs["minutes_per_topic"], prefs["daily_minutes"]),
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
        item_rows = [
            {
                "path_id": path["id"],
                "user_id": user_id,
                "book_id": str(book_id),
                **item.__dict__,
            }
            for item in items
        ]
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
        return {"path": path, "items": items}

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
