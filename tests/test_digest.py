from learnbook.core.ingestion.models import DocumentSection
from learnbook.core.understanding.digest import build_digest


def test_digest_is_deterministic_preserves_page_markers_and_covers_sections() -> None:
    pages = [
        {
            "page_number": 1,
            "text": "Opening filler describes many ordinary details. " * 4
            + (
                "In summary, a key method is deliberate practice because it builds "
                "skill.\n\n"
            ),
        },
        {
            "page_number": 2,
            "text": (
                "The framework is important and always useful. It gives a clear model. "
            )
            * 4,
        },
    ]
    sections = [
        DocumentSection(title="Chapter One", start_page=1, end_page=1, level=1),
        DocumentSection(title="Chapter Two", start_page=2, end_page=2, level=1),
    ]
    first = build_digest(pages, sections=sections, minimum_section_chars=40)
    second = build_digest(pages, sections=sections, minimum_section_chars=40)
    assert first == second
    assert first.sections_covered == first.sections_total == 2
    assert "[p.1]" in first.text and "[p.2]" in first.text
    assert "important" in first.text


def test_empty_and_tiny_sections_keep_sentence_and_validate_size() -> None:
    assert build_digest([]).text == ""
    result = build_digest([{"page_number": 1, "text": "A short useful sentence."}])
    assert "A short useful sentence." in result.text
    try:
        build_digest([], ratio=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid digest ratio was accepted.")
