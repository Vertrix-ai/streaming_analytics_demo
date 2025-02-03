"""Logging configuration for the application."""

import logging
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            str: JSON formatted log entry
        """
        # Base log data
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": "streaming_analytics_demo",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if they exist
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if it exists
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: int = logging.INFO) -> None:
    """Set up logging configuration.

    Args:
        level: The logging level to use
    """
    # Create handler for stdout
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Remove any existing handlers (to avoid duplicates)
    for old_handler in root_logger.handlers[:-1]:
        root_logger.removeHandler(old_handler)
