import logging
import sys
from app.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger() -> None:
    """Configures global logging format and handler."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger configured with the standard system format."""
    return logging.getLogger(name)


class SessionLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically prefixes log lines with the conversation thread ID.
    """
    def __init__(self, logger: logging.Logger, session_id: str):
        super().__init__(logger, {"session_id": session_id})
        self.session_id = session_id

    def process(self, msg, kwargs):
        return f"[{self.session_id}] {msg}", kwargs


# Initialize logger configuration on import
setup_logger()
