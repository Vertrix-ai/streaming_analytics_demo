"""File sink for the streaming analytics demo."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Type

logger = logging.getLogger(__name__)

_sink_registry: Dict[str, Type["Sink"]] = {}


def register_sink(sink_type: str):
    """Register a sink type."""

    def wrapper(cls):
        _sink_registry[sink_type] = cls
        return cls

    return wrapper


def get_sink(config: dict) -> "Sink":
    """Get a sink from the config."""
    sink_type = config.get("type")
    sink_class = _sink_registry.get(sink_type)
    if not sink_class:
        raise ValueError(f"Unknown sink type: {sink_type}")
    return sink_class(config)


class Sink(ABC):
    """Sink that writes messages to a file."""

    def __init__(self, config: dict):
        """Initialize the FileSink."""
        self.config = config

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the sink."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def write(self, message: str) -> None:
        """Write a single message to the file."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the sink."""
        raise NotImplementedError("Subclasses must implement this method")

    def __del__(self):
        """Ensure file is closed when object is garbage collected."""
        self.disconnect()
