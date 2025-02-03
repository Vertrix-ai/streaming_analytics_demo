"""Tests for FileSink."""

import json
import os
import pytest
from pathlib import Path
import yaml
from streaming_analytics_demo.sinks.file_sink import FileSink


@pytest.fixture
def valid_config():
    """Load the valid configuration from fixtures."""
    config_path = Path(__file__).parent.parent / "fixtures" / "valid_config.yml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["sink"]


@pytest.fixture(autouse=True)
def cleanup():
    """Delete test.jsonl before and after each test."""
    # Setup
    if Path("test.jsonl").exists():
        Path("test.jsonl").unlink()

    yield  # Run test

    # Teardown
    if Path("test.jsonl").exists():
        Path("test.jsonl").unlink()


@pytest.fixture
def sink(valid_config):
    """Create a FileSink instance with test configuration."""
    return FileSink(valid_config)


@pytest.mark.asyncio
async def test_connect_disconnect(sink):
    """Test connecting and disconnecting from sink."""
    await sink.connect()
    assert sink._file is not None
    assert sink._file.closed is False
    assert Path(sink.config["file_path"]).exists()
    await sink.disconnect()


@pytest.mark.asyncio
async def test_write_message(sink):
    """Test writing a message to the sink."""
    test_message = {"type": "ticker", "price": "50000.00"}

    await sink.connect()
    await sink.write(json.dumps(test_message))
    await sink.disconnect()

    # Verify file contents
    with open(sink.config["file_path"]) as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert json.loads(lines[0].strip()) == test_message


@pytest.mark.asyncio
async def test_write_multiple_messages(sink):
    """Test writing multiple messages to the sink."""
    messages = [
        {"type": "ticker", "price": "50000.00"},
        {"type": "ticker", "price": "50001.00"},
        {"type": "ticker", "price": "50002.00"},
    ]

    await sink.connect()
    for message in messages:
        await sink.write(json.dumps(message))
    await sink.disconnect()

    # Verify file contents
    with open(sink.config["file_path"]) as f:
        lines = f.readlines()
        assert len(lines) == len(messages)
        for line, expected in zip(lines, messages):
            assert json.loads(line.strip()) == expected


@pytest.mark.asyncio
async def test_write_without_connect(sink):
    """Test that writing without connecting raises an error."""
    with pytest.raises(RuntimeError) as exc_info:
        await sink.write("test message")
    assert "Must connect before writing" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cleanup_on_garbage_collection(valid_config):
    """Test that file is properly closed when sink is garbage collected."""
    sink = FileSink(valid_config)
    await sink.connect()
    await sink.write("test message")

    # Get file descriptor before deletion
    fd = sink._file.fileno()

    # Delete the sink
    del sink

    # Verify file descriptor is closed
    with pytest.raises(OSError):
        os.fstat(fd)
