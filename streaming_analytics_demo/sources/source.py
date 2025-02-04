"""Generic source implementation. This includes the base class and a registry of sources."""

import jsonschema
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Type, ClassVar

logger = logging.getLogger(__name__)

_source_registry: Dict[str, Type["Source"]] = {}


def register_source(source_type: str):
    """Register a source type."""

    def wrapper(cls):
        # Verify the subclass has defined its own config_schema
        if cls.config_schema is Source.config_schema:
            raise TypeError(
                f"Source subclass {cls.__name__} must define its own config_schema"
            )
        _source_registry[source_type] = cls
        return cls

    return wrapper


def get_source(config: dict) -> "Source":
    """Get a source from the config."""
    source_type = config.get("type")
    source_class = _source_registry.get(source_type)
    if not source_class:
        raise ValueError(f"Unknown source type: {source_type}")
    jsonschema.validate(config, source_class.config_schema)
    return source_class(config)


class Source(ABC):
    """Generic source base class."""

    # Class variable to define the configuration schema
    config_schema: ClassVar[dict] = {
        "type": "object",
        "required": ["type"],
        "properties": {"type": {"type": "string"}},
    }

    def __init__(self, config: dict):
        """All sources must be initialized with a config."""
        self.config = config

    def __del__(self):
        """By default, try to disconnect the source when the instance is garbage collected."""
        self.disconnect()

    @abstractmethod
    async def connect(self) -> Any:
        """Connect to the Coinbase WebSocket feed.

        Raises:
            ConnectionError: If connection fails
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the source."""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    async def receive(self) -> Any:
        """Receive messages from the source."""
        raise NotImplementedError("Subclasses must implement this method")
