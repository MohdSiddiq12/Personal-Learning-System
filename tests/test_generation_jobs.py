import asyncio
import json
from pathlib import Path

import pytest

from learnbook.api.provider import CompletionResult
from learnbook.api.summary import generate_book_summary
from learnbook.config import Settings


class FakeProvider:
    def __init__(self, texts: list[str | Exception]) -> None:
        self.texts = texts
        self.calls: list[list[dict[str, str]]] = []

    async def complete(self, messages, max_output_tokens, json_mode=False):
        del max_output_tokens, json_mode
        self.calls.append(messages)
        next_result = self.texts.pop(0)
        if isinstance(next_result, Exception):
            raise next_result
        return CompletionResult(next_result, 20, 10)


def test_map_generation_resumes_after_saved_chunk_results() -> None:
    pages = [
        {"page_number": 1, "text": "first page " * 600},
        {"page_number": 2, "text": "second page " * 600},
    ]
    settings = Settings(_env_file=None)
    first_group = {
        "candidates": [
            {
                "title": "First idea",
                "kind": "topic",
                "summary": "One",
                "importance_guess": 4,
                "page_refs": [1],
                "key_terms": ["first"],
            }
        ]
    }
    final = {
        "overview": "A short overview.",
        "key_ideas": [],
        "frameworks": [],
        "practice": [],
        "topics": [],
    }
    stored: dict[int, dict[str, object]] = {}

    async def save_chunk(index, payload, tokens_in, tokens_out, total):
        assert total >= 1
        assert tokens_in == 20 and tokens_out == 10
        stored[index] = payload

    crashed = FakeProvider(
        [json.dumps(first_group), RuntimeError("simulated worker restart")]
    )
    with pytest.raises(RuntimeError, match="simulated worker restart"):
        asyncio.run(
            generate_book_summary(pages, crashed, settings, on_chunk=save_chunk)
        )
    assert sorted(stored) == [0]

    resumed = FakeProvider([json.dumps(final)])
    result = asyncio.run(
        generate_book_summary(
            pages,
            resumed,
            settings,
            cached_chunks=stored,
            on_chunk=save_chunk,
        )
    )
    assert result.overview == "A short overview."
    assert len(resumed.calls) == 1
    assert "First idea" in resumed.calls[0][1]["content"]


def test_job_migration_has_owner_policies_atomic_budget_and_resume_index() -> None:
    sql = (
        Path("supabase/migrations/202610160001_generation_jobs.sql").read_text().lower()
    )
    for table in ("generation_jobs", "job_chunk_results", "llm_usage_ledger"):
        assert f"alter table public.{table} enable row level security" in sql
    assert "one_active_user_kind" in sql
    assert "pg_advisory_xact_lock" in sql
    assert "budget_exhausted" in sql
    assert "quota_exceeded" in sql
    assert "retry_generation_job" in sql
    assert "on delete cascade" in sql
