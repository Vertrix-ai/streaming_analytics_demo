"""Tests the argument handling of the listen command."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from streaming_analytics_demo.listen import listen


@pytest.fixture
def runner():
    """Fixture for creating a Click runner, needed because we are testing the command line interface."""
    return CliRunner()


def test_listen_with_valid_arguments(runner):
    """Given valid arguments the listen command should parse them correctly and proceed."""
    # Use a valid config file
    config_file = Path(__file__).parent / "fixtures" / "valid_config.yml"

    # Verify the file exists
    assert config_file.exists(), f"Config file not found at {config_file}"

    # Test with valid URL and config file
    result = runner.invoke(
        listen, ["--config", str(config_file), "--url", "http://example.com"]
    )

    assert result.exit_code == 0


def test_listen_missing_arguments(runner):
    """Given missing arguments the listen command should fail."""
    # Test with no arguments
    result = runner.invoke(listen)
    assert result.exit_code != 0
    assert "Missing option" in result.output


def test_listen_invalid_url(runner, tmp_path):
    """Given an invalid URL the listen command should fail."""
    # Create a temporary config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text("test: config")

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
    assert "No such file or directory" in result.output
