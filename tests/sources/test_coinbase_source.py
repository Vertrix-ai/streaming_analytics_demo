"""Tests for the CoinbaseSource class."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from streaming_analytics_demo.sources.coinbase_source import CoinbaseSource


@pytest.fixture
def valid_config():
    """Create a valid configuration dictionary."""
    return {
        "name": "coinbase_bitcoin_ticker",
        "wss_url": "wss://ws-feed.exchange.coinbase.com",
        "type": "coinbase",
        "subscription": {"product_ids": ["BTC-USD"], "channels": ["ticker"]},
    }


@pytest.fixture
def mock_websocket():
    """Create a mock websocket connection."""
    mock_ws = AsyncMock()

    # Mock the send method
    mock_ws.send = AsyncMock()

    # Mock the recv method to return a subscription confirmation
    async def mock_recv():
        return json.dumps({"type": "subscriptions"})

    mock_ws.recv = mock_recv

    return mock_ws


@pytest.mark.asyncio
async def test_connect(valid_config, mock_websocket):
    """Test the connect method establishes connection and subscribes correctly."""
    source = CoinbaseSource(valid_config)

    # Create mock for websockets.connect
    mock_connect = AsyncMock(return_value=mock_websocket)

    with patch("websockets.connect", mock_connect):
        response = await source.connect()
        assert "subscriptions" in str(response)

    # Verify connection was attempted with correct URL
    mock_connect.assert_awaited_once_with(valid_config["wss_url"])

    # Verify subscription message was sent
    expected_subscription = {
        "type": "subscribe",
        "product_ids": valid_config["subscription"]["product_ids"],
        "channels": valid_config["subscription"]["channels"],
    }
    mock_websocket.send.assert_awaited_once_with(json.dumps(expected_subscription))

    # Verify connection state
    assert source._connected is True
    assert source.websocket == mock_websocket


@pytest.mark.asyncio
async def test_connect_invalid_subscription_response(valid_config, mock_websocket):
    """Test that connect raises an error for invalid subscription response."""
    source = CoinbaseSource(valid_config)

    # Mock recv to return an invalid response
    async def mock_recv():
        return json.dumps({"type": "error", "message": "Invalid subscription"})

    mock_websocket.recv = mock_recv

    with patch("websockets.connect", AsyncMock(return_value=mock_websocket)):
        with pytest.raises(ConnectionError) as exc_info:
            await source.connect()

    assert "Failed to subscribe" in str(exc_info.value)
    assert source._connected is False


@pytest.mark.asyncio
async def test_disconnect_when_not_connected(valid_config, mock_websocket):
    """Test disconnection works even when _connected is False."""
    source = CoinbaseSource(valid_config)
    source.websocket = mock_websocket
    source._connected = False  # Explicitly set to False

    await source.disconnect()

    # Verify close was still called
    mock_websocket.close.assert_awaited_once()

    # Verify state
    assert source._connected is False
    assert source.websocket is None
