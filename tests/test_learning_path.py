from pathlib import Path

import pytest

from learnbook.core.learning_path import (
    PathPreferences,
    TopicInput,
    build_learning_path,
)


def test_path_is_parent_first_and_importance_ordered() -> None:
    topics = [
        TopicInput("child-low", "parent", 2, 5, 1),
        TopicInput("parent", None, 1, 5, 0),
        TopicInput("root-high", None, 5, 5, 1),
        TopicInput("child-high", "parent", 5, 5, 0),
    ]
    result = build_learning_path(topics, PathPreferences(10, 10))
    assert [item.topic_id for item in result] == [
        "root-high",
        "parent",
        "child-high",
        "child-low",
    ]
    assert result[0].position == 0
    assert result[1].day_number == 1
    assert result[2].day_number == 2


def test_path_respects_daily_and_topic_budgets_and_marks_leftovers_optional() -> None:
    topics = [
        TopicInput("first", None, 5, 6),
        TopicInput("second", None, 4, 6),
        TopicInput("too-long", None, 3, 11),
    ]
    result = build_learning_path(topics, PathPreferences(10, 10))
    assert [(item.topic_id, item.day_number, item.is_optional) for item in result] == [
        ("first", 1, False),
        ("second", 2, False),
        ("too-long", 2, True),
    ]


def test_empty_path_and_overlong_for_daily_budget() -> None:
    assert build_learning_path([], PathPreferences(10, 30)) == []
    result = build_learning_path(
        [TopicInput("long", None, 5, 8)], PathPreferences(10, 5)
    )
    assert result[0].is_optional


@pytest.mark.parametrize(
    "topics",
    [
        [TopicInput("orphan", "missing", 1, 5)],
        [TopicInput("a", "b", 1, 5), TopicInput("b", "a", 1, 5)],
    ],
)
def test_invalid_hierarchy_is_rejected(topics: list[TopicInput]) -> None:
    with pytest.raises(ValueError):
        build_learning_path(topics, PathPreferences(10, 30))


def test_every_new_table_has_rls_and_owner_policy() -> None:
    sql = Path("supabase/migrations/202610140001_learning_path.sql").read_text()
    tables = [
        "topics",
        "topic_progress",
        "learning_preferences",
        "learning_paths",
        "path_items",
        "highlights",
        "notes",
    ]
    for table in tables:
        assert f"alter table public.{table} enable row level security" in sql.lower()
        assert f"on public.{table} for all to authenticated" in sql.lower()
        assert "using ((select auth.uid()) = user_id)" in sql.lower()
        assert "with check ((select auth.uid()) = user_id)" in sql.lower()
        table_sql = (
            sql.lower()
            .split(f"create table public.{table}", 1)[1]
            .split("create table public.", 1)[0]
        )
        assert "public.books(id) on delete cascade" in table_sql
