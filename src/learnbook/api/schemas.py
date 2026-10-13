"""API response and request models."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

TopicKind = Literal["topic", "subtopic", "framework", "principle", "method"]
TopicStatus = Literal["new", "learning", "understood", "review"]
LearningGoal = Literal["understand", "apply", "review"]


class TopicNode(BaseModel):
    kind: TopicKind
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(max_length=1200)
    importance: int = Field(ge=1, le=5)
    est_minutes: int = Field(ge=1, le=240)
    position: int = Field(ge=0)
    page_refs: list[int] = Field(min_length=1, max_length=100)
    children: list["TopicNode"] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_page_refs(self) -> "TopicNode":
        if any(page < 1 for page in self.page_refs):
            raise ValueError("Page references must be positive.")
        self.page_refs = sorted(set(self.page_refs))
        if any(child.kind == "topic" for child in self.children):
            raise ValueError("A topic cannot be nested beneath another topic.")
        positions = [child.position for child in self.children]
        if len(positions) != len(set(positions)):
            raise ValueError("Sibling topic positions must be unique.")
        return self


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
    topics: list[TopicNode] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def validate_topic_roots(self) -> "BookSummary":
        if any(topic.kind not in ("topic", "framework") for topic in self.topics):
            raise ValueError("Book map roots must be topics or frameworks.")
        positions = [topic.position for topic in self.topics]
        if len(positions) != len(set(positions)):
            raise ValueError("Book map root positions must be unique.")
        return self


class PreferencesInput(BaseModel):
    minutes_per_topic: int = Field(ge=1, le=240)
    daily_minutes: int = Field(ge=1, le=1440)
    goal: LearningGoal


class StatusInput(BaseModel):
    status: TopicStatus


class HighlightInput(BaseModel):
    topic_id: str | None = None
    page: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=4000)
    note: str = Field(default="", max_length=1000)


class NoteInput(BaseModel):
    topic_id: str | None = None
    body: str = Field(min_length=1, max_length=10000)


class RecallAnswer(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=1200)


class TopicLesson(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    recall_questions: list[RecallAnswer] = Field(min_length=2, max_length=2)
    action: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def lesson_length(self) -> "TopicLesson":
        words = len(self.body.split())
        if not 600 <= words <= 900:
            raise ValueError("Lesson body must contain 600 to 900 words.")
        return self


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
