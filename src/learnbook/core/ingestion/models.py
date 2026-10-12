"""Validated result models for PDF extraction."""

from pydantic import BaseModel, Field


class ExtractedPage(BaseModel):
    """Text and basic content indicators for one 1-based PDF page."""

    page_number: int = Field(ge=1)
    text: str
    char_count: int = Field(ge=0)
    is_empty: bool
    has_images: bool


class ExtractedDocument(BaseModel):
    """Extracted document metadata and its ordered pages."""

    title: str | None
    author: str | None
    page_count: int = Field(ge=0)
    pages: list[ExtractedPage]
    sha256: str
    file_size_bytes: int = Field(ge=0)
    needs_ocr: bool
    warnings: list[str]
