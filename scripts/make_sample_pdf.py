"""Generate deterministic text and image-only PDFs for the local demo."""

from pathlib import Path

import pymupdf


def make_text_sample(path: Path) -> None:
    document = pymupdf.open()
    for page_number in range(1, 13):
        page = document.new_page()
        page.insert_text(
            (72, 72),
            f"Chapter {page_number}: Learning from Books",
            fontsize=20,
        )
        page.insert_text(
            (72, 112),
            f"Sample page {page_number}. This is local demo text for page browsing.",
            fontsize=12,
        )
        page.insert_text(
            (72, 145),
            f"Search marker: learnbook-page-{page_number:02d}",
            fontsize=12,
        )
        page.insert_textbox(
            pymupdf.Rect(72, 180, 520, 700),
            f"Chapter {page_number} explores a small idea in detail. " * 16,
            fontsize=11,
        )
    metadata = document.metadata
    metadata["title"] = "LearnBook Sample Book"
    metadata["author"] = "Local Demo"
    document.set_metadata(metadata)
    document.save(path)
    document.close()


def make_scanned_sample(path: Path) -> None:
    document = pymupdf.open()
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 640, 840), 0)
    pixmap.clear_with(248)
    image_bytes = pixmap.tobytes("png")
    for _ in range(12):
        page = document.new_page()
        page.insert_image(pymupdf.Rect(0, 0, 595, 842), stream=image_bytes)
    metadata = document.metadata
    metadata["title"] = "LearnBook Image-Only Sample"
    document.set_metadata(metadata)
    document.save(path)
    document.close()


def main() -> None:
    output_dir = Path("data/samples")
    output_dir.mkdir(parents=True, exist_ok=True)
    text_path = output_dir / "sample_book.pdf"
    scanned_path = output_dir / "sample_scanned.pdf"
    make_text_sample(text_path)
    make_scanned_sample(scanned_path)
    print(f"Created {text_path} (12 text pages)")
    print(f"Created {scanned_path} (12 image-only pages)")


if __name__ == "__main__":
    main()
