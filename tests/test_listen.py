"""Tests the argument handling of the listen command."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from streaming_analytics_demo.listen import listen, _async_listen


@pytest.fixture
def runner():
    """Fixture for creating a Click runner, needed because we are testing the command line interface."""
    return CliRunner()


@pytest.fixture
def mock_coinbase_source():
    """Create a mock CoinbaseSource."""
    # Create instance mock
    mock_source = AsyncMock()
    mock_source.connect = AsyncMock()
    mock_source.disconnect = AsyncMock()
    mock_source.stream = AsyncMock()

    # Mock the async context manager
    mock_source.__aenter__ = AsyncMock(return_value=mock_source)
    mock_source.__aexit__ = AsyncMock()

    # Create class mock
    mock_class = MagicMock()
    mock_class.return_value = mock_source

    return mock_class


def test_listen_with_valid_arguments(runner, mock_coinbase_source):
    """Given valid arguments the listen command should parse them correctly and proceed."""
    config_file = Path(__file__).parent / "fixtures" / "valid_config.yml"
    schema_path = (
        Path(__file__).parent.parent
        / "streaming_analytics_demo"
        / "sources"
        / "config.schema.yaml"
    )

    assert config_file.exists(), f"Config file not found at {config_file}"

    with (
        patch("streaming_analytics_demo.listen.CoinbaseSource", mock_coinbase_source),
        patch(
            "streaming_analytics_demo.listen.CoinbaseSource.get_schema_path",
            return_value=schema_path,
        ),
    ):
        result = runner.invoke(listen, ["--config", str(config_file)])

    assert result.exit_code == 0
    mock_coinbase_source.return_value.connect.assert_awaited_once()


def test_listen_missing_arguments(runner):
    """Given missing arguments the listen command should fail."""
    # Test with no arguments
    result = runner.invoke(listen)
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_listen_nonexistent_config(runner):
    """Given a non-existent config file the listen command should fail."""
    # Test with non-existent config file
    result = runner.invoke(listen, ["--config", "nonexistent.yaml"])
    assert result.exit_code != 0
    assert "does not exist" in result.output


@pytest.mark.asyncio
async def test_async_listen_happy_path():
    """Test the happy path of _async_listen."""
    # Mock source and sink
    source = AsyncMock()
    sink = AsyncMock()

    # Set up source to return 3 messages then raise KeyboardInterrupt
    messages = [
        {"type": "ticker", "price": "50000.00"},
        {"type": "ticker", "price": "50001.00"},
        {"type": "ticker", "price": "50002.00"},
    ]
    source.receive = AsyncMock(side_effect=[*messages, KeyboardInterrupt])

    # Run the listen function
    await _async_listen(source, sink)

    # Verify behavior
    assert source.receive.await_count == len(messages) + 1
    assert sink.write.await_count == len(messages)
    for msg, call in zip(messages, sink.write.await_args_list):
        assert call.args[0] == msg

    # Verify cleanup
    source.disconnect.assert_awaited_once()
    sink.disconnect.assert_awaited_once()


def test_listen_command(runner):
    """Test the listen CLI command end-to-end."""
    config_file = Path(__file__).parent / "fixtures" / "valid_config.yml"

    # Mock both source and sink
    mock_source = AsyncMock()
    mock_sink = AsyncMock()

    # Mock the async functions
    with (
        patch(
            "streaming_analytics_demo.listen._async_connect_source",
            AsyncMock(return_value=mock_source),
        ) as mock_connect_source,
        patch(
            "streaming_analytics_demo.listen._async_connect_sink",
            AsyncMock(return_value=mock_sink),
        ) as mock_connect_sink,
        patch(
            "streaming_analytics_demo.listen._async_listen", AsyncMock()
        ) as mock_listen,
    ):

        result = runner.invoke(listen, ["--config", str(config_file)])

    # Verify the command succeeded
    assert result.exit_code == 0

    # Verify the functions were called in the correct order
    mock_connect_source.assert_awaited_once()
    mock_connect_sink.assert_awaited_once()
    mock_listen.assert_awaited_once_with(mock_source, mock_sink)
