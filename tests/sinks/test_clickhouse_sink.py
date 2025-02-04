"""Test suite for ClickHouse sink."""

import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from streaming_analytics_demo.sinks import get_sink


@pytest.fixture
def valid_config():
    """Load valid ClickHouse configuration from fixture file."""
    config_path = (
        Path(__file__).parent.parent / "fixtures" / "valid_clickhouse_config.yml"
    )
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config["sink"]


@pytest.fixture
def sample_message():
    """Return a sample Coinbase ticker message."""
    return {
        "type": "ticker",
        "sequence": 98545870695,
        "product_id": "BTC-USD",
        "price": "101496.91",
        "open_24h": "93394.63",
        "volume_24h": "27200.49989262",
        "low_24h": "91178.01",
        "high_24h": "102599.85",
        "volume_30d": "390095.33178020",
        "best_bid": "101496.91",
        "best_bid_size": "0.00011127",
        "best_ask": "101496.92",
        "best_ask_size": "0.01060955",
        "side": "sell",
        "time": "2025-02-04T02:00:06.419368Z",
        "trade_id": 774546408,
        "last_size": "0.00001635",
    }


@pytest.fixture
def mock_client():
    """Create a mock ClickHouse client."""
    client = MagicMock()
    client.insert = MagicMock()
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_connect(valid_config, mock_client):
    """Test successful connection to ClickHouse."""
    with patch(
        "streaming_analytics_demo.sinks.clickhouse_sink.clickhouse_connect"
    ) as mock_ch:
        sink = get_sink(valid_config)
        mock_ch.get_client.return_value = mock_client
        await sink.connect()
        assert sink.client == mock_client
        mock_ch.get_client.assert_called_once_with(
            host=valid_config["host"],
            port=valid_config["port"],
            database=valid_config["database"],
            username=valid_config["user"],
            password=valid_config["password"],
            settings={},
        )


@pytest.mark.asyncio
async def test_write_ticker_message(valid_config, mock_client, sample_message):
    """Test writing a ticker message with proper type conversion."""
    with patch(
        "streaming_analytics_demo.sinks.clickhouse_sink.clickhouse_connect"
    ) as mock_ch:
        mock_ch.get_client.return_value = mock_client

        sink = get_sink(valid_config)
        await sink.connect()

        await sink.write(json.dumps(sample_message))

        mock_client.insert.assert_called_once()
        args = mock_client.insert.call_args[1]

        # Verify data types of converted fields
        data = args["data"][0]
        column_names = args["column_names"]
        row_data = dict(zip(column_names, data))

        # Test numeric conversions
        assert isinstance(row_data["sequence"], int)
        assert isinstance(row_data["trade_id"], int)
        assert isinstance(row_data["price"], float)
        assert isinstance(row_data["open_24h"], float)
        assert isinstance(row_data["volume_24h"], float)
        assert isinstance(row_data["low_24h"], float)
        assert isinstance(row_data["high_24h"], float)
        assert isinstance(row_data["volume_30d"], float)
        assert isinstance(row_data["best_bid"], float)
        assert isinstance(row_data["best_bid_size"], float)
        assert isinstance(row_data["best_ask"], float)
        assert isinstance(row_data["best_ask_size"], float)
        assert isinstance(row_data["last_size"], float)

        # Test string fields
        assert isinstance(row_data["product_id"], str)
        assert isinstance(row_data["side"], str)

        # Test datetime conversion
        assert isinstance(row_data["time"], datetime)

        # Verify type field was removed
        assert "type" not in row_data


@pytest.mark.asyncio
async def test_write_without_connection(valid_config):
    """Test writing without connecting first."""
    with patch(
        "streaming_analytics_demo.sinks.clickhouse_sink.clickhouse_connect"
    ) as mock_ch:
        mock_ch.get_client.return_value = MagicMock()
        sink = get_sink(valid_config)
        with pytest.raises(RuntimeError) as exc_info:
            await sink.write('{"test": "data"}')
        assert "Not connected to ClickHouse" in str(exc_info.value)


@pytest.mark.asyncio
async def test_write_invalid_json(valid_config):
    """Test writing invalid JSON."""
    with patch(
        "streaming_analytics_demo.sinks.clickhouse_sink.clickhouse_connect"
    ) as mock_ch:
        mock_ch.get_client.return_value = MagicMock()
        sink = get_sink(valid_config)
        await sink.connect()
        with pytest.raises(json.JSONDecodeError):
            await sink.write("invalid json")


def test_config_validation():
    """Test configuration validation."""
    invalid_config = {
        "type": "clickhouse_connect",
        "host": "localhost",
        "port": 8123,
        # missing database
        "table": "test_table",
        "user": "default",
    }

    with pytest.raises(Exception) as exc_info:
        get_sink(invalid_config)
    assert "database" in str(exc_info.value)

    # Invalid port type
    invalid_config = {
        "type": "clickhouse_connect",
        "host": "localhost",
        "port": "8123",  # should be integer
        "database": "test_db",
        "table": "test_table",
        "user": "default",
    }

    with pytest.raises(Exception) as exc_info:
        get_sink(invalid_config)
    assert "port" in str(exc_info.value)
