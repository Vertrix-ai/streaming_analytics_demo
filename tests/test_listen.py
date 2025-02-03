"""Tests the argument handling of the listen command."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from streaming_analytics_demo.listen import listen


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
        result = runner.invoke(
            listen, ["--config", str(config_file), "--url", "http://example.com"]
        )

    assert result.exit_code == 0
    mock_coinbase_source.return_value.connect.assert_awaited_once()


def test_listen_missing_arguments(runner):
    """Given missing arguments the listen command should fail."""
    # Test with no arguments
    result = runner.invoke(listen)
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_listen_invalid_url(runner):
    """Given an invalid URL the listen command should fail."""
    config_file = Path(__file__).parent / "fixtures" / "valid_config.yml"

    # Test with invalid URL
    result = runner.invoke(listen, ["--config", str(config_file), "--url", "not-a-url"])
    assert result.exit_code != 0
    assert "is not a valid URL" in result.output


def test_listen_nonexistent_config(runner):
    """Given a non-existent config file the listen command should fail."""
    # Test with non-existent config file
    result = runner.invoke(
        listen, ["--config", "nonexistent.yaml", "--url", "http://example.com"]
    )
    assert result.exit_code != 0
    assert "does not exist" in result.output
