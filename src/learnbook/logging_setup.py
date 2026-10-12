"""Basic application logging configuration."""

import logging

from learnbook.config import Settings


def configure_logging(settings: Settings | None = None) -> None:
    """Configure standard logging using the configured level."""
    config = settings or Settings()
    level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
