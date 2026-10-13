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
    minutes_per_topic: int
    daily_minutes: int


@dataclass(frozen=True)
class PathItem:
    topic_id: str
    position: int
    day_number: int
    is_optional: bool


def build_learning_path(
    topics: list[TopicInput], preferences: PathPreferences
) -> list[PathItem]:
    """Return topics parent-first, prioritizing importance within each level.

    Topics too long for a single lesson or a daily session are retained at the
    end as optional items. Cycles and missing parents are rejected.
    """
    if preferences.minutes_per_topic < 1 or preferences.daily_minutes < 1:
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
    while available:
        available.sort(key=lambda item: (-item.importance, item.position, item.id))
        topic = available.pop(0)
        ordered.append(topic)
        available.extend(children.get(topic.id, []))
    if len(ordered) != len(topics):
        raise ValueError("Topic hierarchy cannot contain cycles.")

    result: list[PathItem] = []
    day = 1
    used_minutes = 0
    position = 0
    optional: list[TopicInput] = []
    for topic in ordered:
        if topic.est_minutes < 1:
            raise ValueError("Estimated topic time must be positive.")
        if (
            topic.est_minutes > preferences.minutes_per_topic
            or topic.est_minutes > preferences.daily_minutes
        ):
            optional.append(topic)
            continue
        if used_minutes + topic.est_minutes > preferences.daily_minutes:
            day += 1
            used_minutes = 0
        result.append(PathItem(topic.id, position, day, False))
        position += 1
        used_minutes += topic.est_minutes

    for topic in optional:
        result.append(PathItem(topic.id, position, day, True))
        position += 1
    return result
