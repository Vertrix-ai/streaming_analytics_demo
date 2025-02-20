"""File sink for the streaming analytics demo."""

import logging
from .sink import Sink, register_sink

logger = logging.getLogger(__name__)


@register_sink("file")
class FileSink(Sink):
    """Sink that writes messages to a file."""

    config_schema = {
        "type": "object",
        "required": ["type", "file_path"],
        "properties": {
            "type": {"type": "string", "enum": ["file"]},
            "file_path": {"type": "string"},
        },
        "additionalProperties": False,
    }

    def __init__(self, config: dict):
        """Initialize the FileSink."""
        self.config = config
        self._file = None
        self._file_path = self.config.get("file_path")
        if not self._file_path:
            raise ValueError("file_path is required")

    async def connect(self) -> None:
        """Connect to the sink."""
        self._file = open(self._file_path, "a")

    async def write(self, message: str) -> None:
        """Write a single message to the file."""
        if not self._file or self._file.closed:
            raise RuntimeError("Must connect before writing")

        """Write a message to the file."""
        self._file.write(message + "\n")

    async def disconnect(self) -> None:
        """Disconnect from the sink."""
        if self._file:
            self._file.close()

    def __del__(self):
        """Ensure file is closed when object is garbage collected."""
        if hasattr(self, "file") and self.file:
            self._file.close()
