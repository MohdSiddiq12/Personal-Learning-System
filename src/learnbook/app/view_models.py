"""Pure display transformations for extracted documents."""

from dataclasses import dataclass

from learnbook.core.ingestion.models import ExtractedDocument, ExtractedPage


@dataclass(frozen=True)
class PagePreview:
    """Display data for one selected document page."""

    page_number: int
    text: str
    char_count: int
    is_empty: bool


def summary_rows(document: ExtractedDocument) -> list[tuple[str, str]]:
    """Return safe-to-render labels and values for the document summary."""
    non_empty_pages = sum(not page.is_empty for page in document.pages)
    file_size_mb = document.file_size_bytes / (1024 * 1024)
    return [
        ("Title", document.title or "(untitled)"),
        ("Author", document.author or "(unknown)"),
        ("Page count", str(document.page_count)),
        ("File size", f"{file_size_mb:.2f} MB"),
        ("SHA-256", document.sha256[:12]),
        ("Non-empty pages", str(non_empty_pages)),
        ("Needs OCR", str(document.needs_ocr)),
    ]


def page_preview(document: ExtractedDocument, page_number: int) -> PagePreview:
    """Return display data for a 1-based page number."""
    if page_number < 1 or page_number > document.page_count:
        raise ValueError("page_number must be within the document page range")
    page: ExtractedPage = document.pages[page_number - 1]
    return PagePreview(
        page_number=page.page_number,
        text=page.text,
        char_count=page.char_count,
        is_empty=page.is_empty,
    )


def export_text(document: ExtractedDocument) -> str:
    """Format all pages as plain text with explicit page boundaries."""
    return "\n\n".join(
        f"=== Page {page.page_number} ===\n{page.text}" for page in document.pages
    )


def search_pages(document: ExtractedDocument, query: str) -> list[int]:
    """Return page numbers containing a case-insensitive literal substring."""
    if not query:
        return []
    needle = query.casefold()
    return [
        page.page_number for page in document.pages if needle in page.text.casefold()
    ]
