"""Coinbase WebSocket source implementation."""

import json
import logging
from pathlib import Path
from typing import Dict, Any
import websockets

logger = logging.getLogger(__name__)


class CoinbaseSource:
    """Source implementation for Coinbase WebSocket API."""

    @classmethod
    def get_schema_path(cls) -> Path:
        """Get the path to the schema file for this source.

        Returns:
            Path: Path to the schema file
        """
        return Path(__file__).parent / "config.schema.yaml"

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Coinbase source.

        Args:
            config: Configuration dictionary validated against the schema
        """
        self.config = config
        self.websocket = None
        self._connected = False
        logger.info("Coinbase source initialized")

    async def connect(self) -> None:
        """Connect to the Coinbase WebSocket feed.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to Coinbase WebSocket feed")
            self.websocket = await websockets.connect(self.config["wss_url"])
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
                raise ConnectionError(
                    "Failed to subscribe to the Coinbase WebSocket feed"
                )
        except Exception as e:
            logger.error("Lost connection to Coinbase WebSocket feed: %s", str(e))
            raise ConnectionError(f"Lost connection to Coinbase WebSocket feed: {e}")
