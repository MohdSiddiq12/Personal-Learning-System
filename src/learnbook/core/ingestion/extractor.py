"""Validate PDF input and extract normalized text without rendering pages."""

import hashlib
import logging
import re
import unicodedata
from pathlib import Path

import pymupdf

from learnbook.config import Settings
from learnbook.core.ingestion.errors import (
    EmptyDocumentError,
    EncryptedPdfError,
    FileTooLargeError,
    IngestionError,
    InvalidPdfError,
    TooManyPagesError,
)
from learnbook.core.ingestion.models import (
    DocumentSection,
    ExtractedDocument,
    ExtractedPage,
)

logger = logging.getLogger(__name__)
_OCR_WARNING = "Most pages contain little text; this document may be scanned."


def _size_limit_bytes(settings: Settings) -> int:
    return settings.max_upload_mb * 1024 * 1024


def _read_source(source: Path | bytes, settings: Settings) -> bytes:
    limit = _size_limit_bytes(settings)

    if isinstance(source, bytes):
        file_bytes = source
    else:
        try:
            if source.stat().st_size > limit:
                raise FileTooLargeError()
            with source.open("rb") as file:
                file_bytes = file.read(limit + 1)
        except FileTooLargeError:
            raise
        except OSError as exc:
            raise InvalidPdfError() from exc

    if len(file_bytes) > limit:
        raise FileTooLargeError()
    if not file_bytes.startswith(b"%PDF-"):
        raise InvalidPdfError()
    return file_bytes


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "".join(
        character
        for character in normalized
        if character == "\n" or unicodedata.category(character) != "Cc"
    )
    return re.sub(r" {2,}", " ", normalized).strip()


def _clean_metadata(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = "".join(
        character for character in value if unicodedata.category(character) != "Cc"
    )
    cleaned = cleaned.strip()[:200]
    return cleaned or None


def _outline_sections(document, page_count: int) -> list[DocumentSection]:
    sections: list[DocumentSection] = []
    try:
        outline = document.get_toc()
    except Exception:
        return sections
    entries = [
        (int(level), str(title).strip(), int(page))
        for level, title, page, *_ in outline
        if str(title).strip() and 1 <= int(page) <= page_count
    ]
    for index, (level, title, start_page) in enumerate(entries):
        next_page = next(
            (
                page
                for next_level, _, page in entries[index + 1 :]
                if next_level <= level
            ),
            page_count + 1,
        )
        end_page = max(start_page, min(page_count, next_page - 1))
        sections.append(
            DocumentSection(
                title=_clean_metadata(title) or "Section",
                start_page=start_page,
                end_page=end_page,
                level=max(1, min(level, 10)),
            )
        )
    return sections


def extract_pdf(source: Path | bytes, settings: Settings) -> ExtractedDocument:
    """Validate a PDF and return its normalized text in original page order."""
    file_bytes = _read_source(source, settings)
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    try:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
            if document.is_encrypted or document.needs_pass:
                raise EncryptedPdfError()

            page_count = document.page_count
            if page_count == 0:
                raise EmptyDocumentError()
            if page_count > settings.max_pages:
                raise TooManyPagesError()

            pages: list[ExtractedPage] = []
            for index in range(page_count):
                page = document.load_page(index)
                text = _normalize_text(page.get_text("text"))
                char_count = len(text)
                pages.append(
                    ExtractedPage(
                        page_number=index + 1,
                        text=text,
                        char_count=char_count,
                        is_empty=char_count < settings.min_chars_per_page,
                        has_images=bool(page.get_images(full=True)),
                    )
                )

            metadata = document.metadata or {}
            title = _clean_metadata(metadata.get("title"))
            author = _clean_metadata(metadata.get("author"))
            sections = _outline_sections(document, page_count)
    except IngestionError:
        raise
    except Exception as exc:
        raise InvalidPdfError() from exc

    empty_pages = sum(page.is_empty for page in pages)
    needs_ocr = empty_pages / page_count >= settings.ocr_suspect_ratio
    warnings = [_OCR_WARNING] if needs_ocr else []

    logger.info(
        "PDF extraction completed: pages=%d bytes=%d sha256=%s",
        page_count,
        len(file_bytes),
        sha256[:12],
    )
    return ExtractedDocument(
        title=title,
        author=author,
        page_count=page_count,
        pages=pages,
        sha256=sha256,
        file_size_bytes=len(file_bytes),
        needs_ocr=needs_ocr,
        warnings=warnings,
        sections=sections,
        structure_source="outline" if sections else "fallback",
    )
