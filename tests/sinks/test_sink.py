"""Test ability to register and get custom sinks."""

from streaming_analytics_demo.sinks import get_sink, register_sink, Sink
from streaming_analytics_demo.sinks import FileSink


@register_sink("test")
class TestSink(Sink):
    """Test sink that does nothing."""

    config_schema = {
        "type": "object",
        "required": ["type"],
        "properties": {"type": {"type": "string"}},
    }

    def __init__(self, config: dict):
        """Initialize the test sink."""
        super().__init__(config)

    async def connect(self) -> None:
        """Connect to the test sink."""
        pass

    async def write(self, message: str) -> None:
        """Write to the test sink."""
        pass

    async def disconnect(self) -> None:
        """Disconnect from the test sink."""
        pass


def test_get_custom_sink():
    """Test that get_sink returns the correct sink."""
    sink = get_sink({"type": "test"})
    assert isinstance(sink, TestSink)


def test_get_core_sink():
    """Test that get_sink returns the correct sink."""
    sink = get_sink({"type": "file", "file_path": "test.txt"})
    assert isinstance(sink, FileSink)
