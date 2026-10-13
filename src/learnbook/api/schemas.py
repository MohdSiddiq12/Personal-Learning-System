"""API response and request models."""

from pydantic import BaseModel, Field


class Idea(BaseModel):
    title: str = Field(max_length=160)
    explanation: str = Field(max_length=1200)
    pages: list[int] = Field(min_length=1)


class PracticeQuestion(BaseModel):
    question: str = Field(max_length=500)
    suggested_action: str = Field(max_length=700)
    pages: list[int] = Field(min_length=1)


class BookSummary(BaseModel):
    overview: str = Field(max_length=2200)
    key_ideas: list[Idea] = Field(max_length=12)
    frameworks: list[Idea] = Field(max_length=8)
    practice: list[PracticeQuestion] = Field(max_length=5)


class GenerateSummaryRequest(BaseModel):
    data_use_consent: bool


class BookRecord(BaseModel):
    id: str
    title: str | None = None
    author: str | None = None
    page_count: int
    file_size_bytes: int
    needs_ocr: bool
    created_at: str | None = None
    summary_json: BookSummary | None = None


class UploadedBook(BookRecord):
    duplicate: bool = False
