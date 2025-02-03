"""Test suite for configuration validation."""

import pytest
from pathlib import Path
from click import BadParameter
from streaming_analytics_demo.listen import build_config


def test_valid_config():
    """Test that a valid configuration file is accepted."""
    config_path = Path(__file__).parent / "fixtures" / "valid_config.yml"
    config = build_config(config_path)
    # Check structure
    assert "source" in config
    assert "wss_url" in config["source"]
    assert "type" in config["source"]
    assert "subscription" in config["source"]

    # Check values
    assert config["source"]["type"] == "coinbase"
    assert config["source"]["name"] == "coinbase_bitcoin_ticker"
    assert isinstance(config["source"]["subscription"]["product_ids"], list)
    assert isinstance(config["source"]["subscription"]["channels"], list)


def test_missing_required_fields():
    """Test that missing required fields raise appropriate errors."""
    config_path = Path(__file__).parent / "fixtures" / "config_missing_reqd_fields.yml"
    with pytest.raises(BadParameter) as exc_info:
        build_config(config_path)
    assert "required property" in str(exc_info.value)


def test_invalid_type():
    """Test that an invalid type raises an error."""
    config_path = Path(__file__).parent / "fixtures" / "config_invalid_type.yml"
    with pytest.raises(BadParameter) as exc_info:
        build_config(config_path)
    assert "is not one of" in str(exc_info.value)
