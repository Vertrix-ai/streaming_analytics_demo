"""Coinbase WebSocket source implementation."""

import json
from pathlib import Path
from typing import Dict, Any
import websockets
from websockets.client import WebSocketClientProtocol


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
        self.websocket: WebSocketClientProtocol | None = None

    async def connect(self) -> None:
        """Connect to the Coinbase WebSocket feed.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.websocket = await websockets.connect(self.config["wss_url"])

            # Build subscription message
            subscribe_message = {
                "type": "subscribe",
                "product_ids": self.config["subscription"]["product_ids"],
                "channels": self.config["subscription"]["channels"],
            }

            # Send subscription
            await self.websocket.send(json.dumps(subscribe_message))

            # Wait for subscription confirmation
            response = await self.websocket.recv()
            response_data = json.loads(response)
            if response_data.get("type") != "subscriptions":
                raise ConnectionError(
                    "Failed to subscribe to the Coinbase WebSocket feed"
                )
        except Exception as e:
            raise ConnectionError(f"Lost connection to Coinbase WebSocket feed: {e}")
