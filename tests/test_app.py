from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "src" / "learnbook" / "app" / "main.py"


def make_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH)).run()


def upload_pdf(app: AppTest, name: str, content: bytes) -> AppTest:
    app.file_uploader[0].set_value((name, content, "application/pdf"))
    return app.run()


def test_app_uploads_valid_pdf_and_browses_first_page(text_pdf: Path) -> None:
    app = upload_pdf(make_app(), "sample.pdf", text_pdf.read_bytes())

    assert not app.exception
    assert app.title[0].value == "LearnBook"
    assert any(item.label == "Pages" and item.value == "3" for item in app.metric)
    assert "Page one unique text" in app.text_area[0].value


def test_app_reports_a_pdf_uploaded_again_in_the_same_session(text_pdf: Path) -> None:
    content = text_pdf.read_bytes()
    app = upload_pdf(make_app(), "sample.pdf", content)
    app.file_uploader[0].set_value(None)
    app.run()
    app = upload_pdf(app, "sample.pdf", content)

    assert any("already been uploaded" in item.value for item in app.info)


def test_app_search_result_jumps_to_matching_page(text_pdf: Path) -> None:
    app = upload_pdf(make_app(), "sample.pdf", text_pdf.read_bytes())
    app.text_input(key="search_query").set_value("Page two unique text").run()

    app.button(key="open-search-result").click().run()

    assert app.number_input(key="page_number").value == 2
    assert "Page two unique text" in app.text_area[0].value


def test_app_shows_plain_error_for_corrupt_pdf() -> None:
    app = upload_pdf(make_app(), "corrupt.pdf", b"%PDF-not a valid document")

    assert not app.exception
    assert app.error[0].value == "This file is not a valid, readable PDF."


def test_app_rejects_wrong_file_content_with_pdf_extension() -> None:
    app = upload_pdf(make_app(), "notes.pdf", b"This is a text file, not a PDF.")

    assert not app.exception
    assert app.error[0].value == "This file is not a valid, readable PDF."


def test_app_shows_plain_error_for_oversize_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    content = b"%PDF-" + b"0" * (1024 * 1024)
    app = upload_pdf(make_app(), "oversize.pdf", content)

    assert not app.exception
    assert app.error[0].value == "This PDF exceeds the configured upload size limit."


def test_app_shows_plain_error_for_encrypted_pdf(encrypted_pdf: Path) -> None:
    app = upload_pdf(make_app(), "encrypted.pdf", encrypted_pdf.read_bytes())

    assert not app.exception
    assert (
        app.error[0].value == "This PDF is password-protected and cannot be processed."
    )
