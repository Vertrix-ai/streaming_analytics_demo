"""Coinbase WebSocket source implementation."""

import asyncio
import json
import logging
from typing import Dict, Any
import warnings
import websockets

from .source import Source, register_source

logger = logging.getLogger(__name__)


@register_source("coinbase")
class CoinbaseSource(Source):
    """Source implementation for Coinbase WebSocket API."""

    config_schema = {
        "type": "object",
        "required": ["wss_url", "type", "subscription"],
        "properties": {
            "wss_url": {
                "type": "string",
                "format": "uri-reference",
                "pattern": "^wss?://",
            },
            "type": {"type": "string", "enum": ["coinbase"]},
            "subscription": {
                "type": "object",
                "required": ["product_ids", "channels"],
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {"type": "string", "pattern": "^[A-Z]+-[A-Z]+$"},
                    },
                    "channels": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "type": "string",
                            "enum": [
                                "ticker",
                                "level2",
                                "matches",
                                "full",
                                "heartbeat",
                            ],
                        },
                    },
                },
            },
        },
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Coinbase source.

        Args:
            config: Configuration dictionary validated against the schema
        """
        self.config = config
        self.websocket = None
        self._connected = False
        self._loop = None
        logger.info("Coinbase source initialized")

    def __del__(self):
        """Ensure websocket is closed when the instance is garbage collected."""
        if self.websocket:
            if self._loop and self._loop.is_running():
                # We're in an event loop, we can run disconnect
                asyncio.create_task(self.disconnect())
            else:
                warnings.warn(
                    "CoinbaseSource was garbage collected with a websocket still open "
                    "and no running event loop to clean it up.",
                    ResourceWarning,
                    source=self,
                )

    async def connect(self) -> Any:
        """Connect to the Coinbase WebSocket feed.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to Coinbase WebSocket feed")
            url = self.config.get("wss_url")
            self.websocket = await websockets.connect(url)
            logger.info("Connected to Coinbase WebSocket feed")
            self._connected = True
            # Build subscription message
            subscribe_message = {
                "type": "subscribe",
                "product_ids": self.config["subscription"]["product_ids"],
                "channels": self.config["subscription"]["channels"],
            }
            logger.info("Sending subscription message: %s", subscribe_message)
            # Send subscription
            await self.websocket.send(json.dumps(subscribe_message))
            logger.info("Subscription message sent")
            # Wait for subscription confirmation
            response = await self.websocket.recv()
            logger.info("Subscription confirmation received: %s", str(response))
            response_data = json.loads(response)
            if response_data.get("type") != "subscriptions":
                logger.error(
                    "Failed to subscribe to the Coinbase WebSocket feed: %s",
                    str(response_data),
                )
                await self.disconnect()
                raise ConnectionError(
                    "Failed to subscribe to the Coinbase WebSocket feed"
                )
        except Exception as e:
            await self.disconnect()

            logger.error("Lost connection to Coinbase WebSocket feed: %s", str(e))
            raise ConnectionError(f"Lost connection to Coinbase WebSocket feed: {e}")
        return response_data

    async def disconnect(self) -> None:
        """Gracefully disconnect from the WebSocket feed."""
        try:
            logger.info("Disconnecting from Coinbase WebSocket feed")
            await self.websocket.close()
            logger.info("Disconnected from Coinbase WebSocket feed")
        except Exception as e:
            logger.error("Error during disconnect: %s", str(e))
        finally:
            self._connected = False
            self.websocket = None

    async def receive(self) -> Any:
        """Receive messages from the Coinbase WebSocket feed."""
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except Exception as e:
            logger.error("Error receiving message: %s", str(e))
            await self.disconnect()
            raise e
