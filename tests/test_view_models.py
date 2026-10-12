from learnbook.app.view_models import (
    export_text,
    page_preview,
    search_pages,
    summary_rows,
)
from learnbook.core.ingestion.models import ExtractedDocument, ExtractedPage


def make_document() -> ExtractedDocument:
    pages = [
        ExtractedPage(
            page_number=1,
            text="A unique opening page",
            char_count=22,
            is_empty=False,
            has_images=False,
        ),
        ExtractedPage(
            page_number=2,
            text="second page has a Needle",
            char_count=26,
            is_empty=False,
            has_images=False,
        ),
        ExtractedPage(
            page_number=3,
            text="",
            char_count=0,
            is_empty=True,
            has_images=True,
        ),
    ]
    return ExtractedDocument(
        title="Sample Book",
        author="A. Reader",
        page_count=3,
        pages=pages,
        sha256="abcdef0123456789",
        file_size_bytes=1024 * 1024,
        needs_ocr=False,
        warnings=[],
    )


def test_summary_rows_include_required_document_facts() -> None:
    rows = summary_rows(make_document())

    assert rows == [
        ("Title", "Sample Book"),
        ("Author", "A. Reader"),
        ("Page count", "3"),
        ("File size", "1.00 MB"),
        ("SHA-256", "abcdef012345"),
        ("Non-empty pages", "2"),
        ("Needs OCR", "False"),
    ]


def test_page_preview_returns_selected_page_fields() -> None:
    preview = page_preview(make_document(), 2)

    assert preview.page_number == 2
    assert preview.text == "second page has a Needle"
    assert preview.char_count == 26
    assert not preview.is_empty


def test_page_preview_rejects_out_of_range_page() -> None:
    try:
        page_preview(make_document(), 4)
    except ValueError as error:
        assert "page_number" in str(error)
    else:
        raise AssertionError("out-of-range page did not raise ValueError")


def test_export_text_marks_each_page() -> None:
    assert export_text(make_document()) == (
        "=== Page 1 ===\nA unique opening page\n\n"
        "=== Page 2 ===\nsecond page has a Needle\n\n"
        "=== Page 3 ===\n"
    )


def test_search_is_case_insensitive_and_returns_multiple_pages() -> None:
    document = make_document()
    document.pages[0].text = "Needle appears here"

    assert search_pages(document, "NEEDLE") == [1, 2]


def test_search_returns_no_pages_for_empty_query_or_no_match() -> None:
    document = make_document()

    assert search_pages(document, "") == []
    assert search_pages(document, "missing") == []
