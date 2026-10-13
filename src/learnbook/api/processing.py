"""Run potentially pathological PDF parsing in a terminable child process."""

import multiprocessing
from multiprocessing.connection import Connection

from learnbook.config import Settings
from learnbook.core.ingestion.errors import (
    EmptyDocumentError,
    EncryptedPdfError,
    FileTooLargeError,
    IngestionError,
    InvalidPdfError,
    PdfProcessingTimeoutError,
    TooManyPagesError,
)
from learnbook.core.ingestion.extractor import extract_pdf
from learnbook.core.ingestion.models import ExtractedDocument

_ERRORS: dict[str, type[IngestionError]] = {
    error.__name__: error
    for error in (
        EmptyDocumentError,
        EncryptedPdfError,
        FileTooLargeError,
        InvalidPdfError,
        TooManyPagesError,
    )
}


def _parse_in_child(
    connection: Connection, file_bytes: bytes, settings_values: dict[str, object]
) -> None:
    try:
        settings = Settings(_env_file=None, **settings_values)
        document = extract_pdf(file_bytes, settings)
        connection.send(("ok", document.model_dump(mode="json")))
    except IngestionError as error:
        connection.send(("error", type(error).__name__))
    except Exception:
        connection.send(("error", "InvalidPdfError"))
    finally:
        connection.close()


def extract_pdf_with_timeout(
    file_bytes: bytes,
    settings: Settings,
    timeout_seconds: int,
) -> ExtractedDocument:
    """Extract in a spawned process and terminate it after the hard deadline."""
    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    settings_values: dict[str, object] = {
        "max_upload_mb": settings.max_upload_mb,
        "max_pages": settings.max_pages,
        "min_chars_per_page": settings.min_chars_per_page,
        "ocr_suspect_ratio": settings.ocr_suspect_ratio,
    }
    process = context.Process(
        target=_parse_in_child,
        args=(child_connection, file_bytes, settings_values),
        daemon=True,
    )
    try:
        process.start()
    except Exception as error:
        parent_connection.close()
        child_connection.close()
        raise InvalidPdfError() from error
    child_connection.close()

    try:
        if not parent_connection.poll(timeout_seconds):
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            raise PdfProcessingTimeoutError()
        try:
            status, payload = parent_connection.recv()
        except EOFError as error:
            raise InvalidPdfError() from error
    finally:
        parent_connection.close()
        if process.is_alive():
            process.join(timeout=0.5)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join()

    if status == "error":
        error_type = _ERRORS.get(str(payload), InvalidPdfError)
        raise error_type()
    try:
        document = ExtractedDocument.model_validate(payload)
        return document.model_copy(
            update={
                "sections": [
                    section.model_dump(mode="json") for section in document.sections
                ],
                "structure_source": document.structure_source,
            }
        )
    except Exception as error:
        raise InvalidPdfError() from error
