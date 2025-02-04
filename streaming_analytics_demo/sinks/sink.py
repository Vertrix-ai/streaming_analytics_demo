"""Generic sink implementation. This includes the base class and a registry of sinks."""

import jsonschema
import logging
from abc import ABC, abstractmethod
from typing import Dict, Type, ClassVar

logger = logging.getLogger(__name__)

_sink_registry: Dict[str, Type["Sink"]] = {}


def register_sink(sink_type: str):
    """Register a sink type."""

    def wrapper(cls):
        # Verify the subclass has defined its own config_schema
        if cls.config_schema is Sink.config_schema:
            raise TypeError(
                f"Sink subclass {cls.__name__} must define its own config_schema"
            )
        _sink_registry[sink_type] = cls
        return cls

    return wrapper


def get_sink(config: dict) -> "Sink":
    """Get a sink from the config."""
    sink_type = config.get("type")
    sink_class = _sink_registry.get(sink_type)
    if not sink_class:
        raise ValueError(f"Unknown sink type: {sink_type}")
    jsonschema.validate(config, sink_class.config_schema)
    return sink_class(config)


class Sink(ABC):
    """Generic sink base class."""

    # Class variable to define the configuration schema
    config_schema: ClassVar[dict] = {
        "type": "object",
        "required": ["type"],
        "properties": {"type": {"type": "string"}},
    }

    def __init__(self, config: dict):
        """All sinks must be initialized with a config."""
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
