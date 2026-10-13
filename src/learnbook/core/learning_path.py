"""Deterministic learning-path scheduling independent of API and storage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicInput:
    id: str
    parent_id: str | None
    importance: int
    est_minutes: int
    position: int = 0


@dataclass(frozen=True)
class PathPreferences:
    daily_minutes: int
    completed_topic_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PathItem:
    topic_id: str
    position: int
    day_number: int
    is_optional: bool
    minutes_allocated: int = 0
    is_condensed: bool = False
    completed_at: str | None = None


def build_learning_path(
    topics: list[TopicInput], preferences: PathPreferences
) -> list[PathItem]:
    """Return topics parent-first, prioritizing importance within each level.

    Topics too long for a single lesson or a daily session are retained at the
    end as optional items. Cycles and missing parents are rejected.
    """
    if not 5 <= preferences.daily_minutes <= 180:
        raise ValueError("Learning time budgets must be positive.")
    by_id = {topic.id: topic for topic in topics}
    if len(by_id) != len(topics):
        raise ValueError("Topic ids must be unique.")
    for topic in topics:
        if topic.parent_id is not None and topic.parent_id not in by_id:
            raise ValueError("Every parent id must refer to a topic in the path.")

    children: dict[str, list[TopicInput]] = {}
    available = [item for item in topics if item.parent_id is None]
    for topic in topics:
        if topic.parent_id is not None:
            children.setdefault(topic.parent_id, []).append(topic)
    ordered: list[TopicInput] = []
    optional_ids = {topic.id for topic in topics if topic.importance <= 2}
    for topic in topics:
        parent = topic.parent_id
        while parent is not None:
            if parent in optional_ids:
                optional_ids.add(topic.id)
                break
            parent = by_id[parent].parent_id
    while available:
        available.sort(
            key=lambda item: (
                item.importance <= 2,
                -item.importance,
                item.position,
                item.id,
            )
        )
        next_level: list[TopicInput] = []
        for topic in available:
            ordered.append(topic)
            next_level.extend(children.get(topic.id, []))
        available = next_level
    if len(ordered) != len(topics):
        raise ValueError("Topic hierarchy cannot contain cycles.")

    result: list[PathItem] = []
    day = 1
    used_minutes = 0
    position = 0
    optional: list[TopicInput] = []
    ordered = [
        topic for topic in ordered if topic.id not in preferences.completed_topic_ids
    ]
    for topic in ordered:
        if topic.est_minutes < 1:
            raise ValueError("Estimated topic time must be positive.")
        if topic.id in optional_ids:
            optional.append(topic)
            continue
        allocated = min(topic.est_minutes, preferences.daily_minutes)
        if used_minutes + allocated > preferences.daily_minutes:
            day += 1
            used_minutes = 0
        result.append(
            PathItem(
                topic.id,
                position,
                day,
                False,
                allocated,
                topic.est_minutes > preferences.daily_minutes,
            )
        )
        position += 1
        used_minutes += allocated

    for topic in optional:
        allocated = min(topic.est_minutes, preferences.daily_minutes)
        if used_minutes + allocated > preferences.daily_minutes:
            day += 1
            used_minutes = 0
        result.append(
            PathItem(
                topic.id,
                position,
                day,
                True,
                allocated,
                topic.est_minutes > preferences.daily_minutes,
            )
        )
        position += 1
        used_minutes += allocated
    return result
