"""Command-line interface for inspecting a PDF extraction result."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from learnbook.config import Settings
from learnbook.core.ingestion.errors import IngestionError
from learnbook.core.ingestion.extractor import extract_pdf


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract text from a PDF file.")
    parser.add_argument("path", type=Path, help="Path to the PDF file")
    args = parser.parse_args(arguments)

    try:
        document = extract_pdf(args.path, Settings())
    except IngestionError as error:
        print(error.user_message, file=sys.stderr)
        return 1

    print(f"Title: {document.title or '(untitled)'}")
    print(f"Pages: {document.page_count}")
    print(f"Needs OCR: {document.needs_ocr}")
    print(f"SHA-256: {document.sha256[:12]}")
    print(f"Warnings: {', '.join(document.warnings) or 'none'}")
    print(f"Page 1 preview: {document.pages[0].text[:300]}")
    return 0
