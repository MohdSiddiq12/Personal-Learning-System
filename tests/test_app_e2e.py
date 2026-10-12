import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright


@pytest.mark.e2e
def test_local_pdf_upload_browse_search_and_errors(tmp_path: Path) -> None:
    base_url = os.environ.get("LEARNBOOK_APP_URL", "http://localhost:8501")
    sample_dir = Path("data/samples")
    screenshots = Path("data/screenshots")
    screenshots.mkdir(parents=True, exist_ok=True)
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-not a valid document")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.environ.get("LEARNBOOK_CHROMIUM_EXECUTABLE"),
        )
        page = browser.new_page()
        page.goto(base_url, wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="LearnBook")).to_be_visible()

        uploader = page.locator('input[type="file"]')
        expect(uploader).to_be_attached()
        uploader.set_input_files(str(sample_dir / "sample_book.pdf"))
        expect(page.get_by_text("Page count: 12", exact=True)).to_be_visible()
        page_text = page.get_by_role("textbox", name="Page text")
        expect(page_text).to_have_value(re.compile("learnbook-page-01"))
        page.screenshot(path=str(screenshots / "success.png"), full_page=True)

        page.get_by_role("button", name="Next page").click()
        expect(page_text).to_have_value(re.compile("learnbook-page-02"))

        search_box = page.get_by_role("textbox", name="Search text")
        search_box.fill("learnbook-page-05")
        search_box.press("Enter")
        page.get_by_role("button", name="Go to selected result").click()
        expect(page_text).to_have_value(re.compile("learnbook-page-05"))

        with page.expect_download() as download_info:
            page.get_by_role("button", name="Download extracted text").click()
        download = download_info.value
        export_path = tmp_path / "learnbook-extracted.txt"
        download.save_as(str(export_path))
        assert "=== Page 1 ===" in export_path.read_text(encoding="utf-8")
        assert "=== Page 12 ===" in export_path.read_text(encoding="utf-8")

        uploader.set_input_files(str(sample_dir / "sample_scanned.pdf"))
        expect(
            page.get_by_text(
                "This looks like a scanned PDF. Text extraction is unreliable "
                "until OCR is added."
            )
        ).to_be_visible()

        uploader.set_input_files(str(corrupt_pdf))
        expect(
            page.get_by_text("This file is not a valid, readable PDF.")
        ).to_be_visible()
        expect(page.get_by_text(re.compile("Traceback"))).to_have_count(0)
        page.screenshot(path=str(screenshots / "error.png"), full_page=True)
        browser.close()
