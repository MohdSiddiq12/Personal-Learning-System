"""User-facing errors raised while validating or extracting a PDF."""


class IngestionError(Exception):
    """Base class for an error that can be safely shown to the user."""

    user_message = "The document could not be processed."

    def __init__(self) -> None:
        super().__init__(self.user_message)


class InvalidPdfError(IngestionError):
    """Raised for non-PDF, zero-byte, corrupt, or unreadable input."""

    user_message = "This file is not a valid, readable PDF."


class EncryptedPdfError(IngestionError):
    """Raised when a PDF requires a password."""

    user_message = "This PDF is password-protected and cannot be processed."


class FileTooLargeError(IngestionError):
    """Raised when the input exceeds the configured upload size limit."""

    user_message = "This PDF exceeds the configured upload size limit."


class TooManyPagesError(IngestionError):
    """Raised when the input exceeds the configured page limit."""

    user_message = "This PDF exceeds the configured page limit."


class EmptyDocumentError(IngestionError):
    """Raised when a valid PDF contains no pages."""

    user_message = "This PDF contains no pages."
