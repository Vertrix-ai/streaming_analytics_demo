"""ClickHouse sink implementation."""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from .sink import Sink, register_sink

logger = logging.getLogger(__name__)

_message_field_types = {
    "sequence": int,
    "trade_id": int,
    "price": float,
    "last_size": float,
    "time": datetime.fromisoformat,
    "product_id": str,
    "side": str,
    "open_24h": float,
    "volume_24h": float,
    "low_24h": float,
    "high_24h": float,
    "volume_30d": float,
    "best_bid": float,
    "best_bid_size": float,
    "best_ask": float,
    "best_ask_size": float,
}


@register_sink("clickhouse_connect")
class ClickHouseConnectSink(Sink):
    """Sink that writes messages to ClickHouse."""

    config_schema = {
        "type": "object",
        "required": ["type", "host", "port", "database", "table", "user"],
        "properties": {
            "type": {"type": "string", "enum": ["clickhouse_connect"]},
            "host": {"type": "string"},
            "port": {"type": "integer"},
            "database": {"type": "string"},
            "table": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "settings": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize the ClickHouse sink."""
        super().__init__(config)
        self.client: Client | None = None
        self.database = config["database"]
        self.table = config["table"]

    async def connect(self) -> None:
        """Connect to ClickHouse."""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                username=self.config["user"],
                password=self.config.get("password"),
                settings=self.config.get("settings", {}),
            )
            logger.info(
                f"Connected to ClickHouse at {self.config['host']}:{self.config['port']}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise e

    def _convert_types(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert the data to the correct types for ClickHouse."""
        for key, value in data.items():
            if key in _message_field_types:
                data[key] = _message_field_types[key](value)
        return data

    async def write(self, message: str) -> None:
        """Write a message to ClickHouse.

        Args:
            message: JSON string containing the data to write
        """
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        try:
            # Parse the JSON message
            data = json.loads(message)
            data.pop("type")  # Remove the type key,

            data = self._convert_types(data)
            # Convert to list of values if it's a single record
            if not isinstance(data, list):
                data = [data]

            # Extract column names from the first record
            columns = list(data[0].keys())

            # Extract values maintaining column order
            values = [[record[col] for col in columns] for record in data]

            # Insert the data
            self.client.insert(table=self.table, data=values, column_names=columns)

            logger.debug(
                f"Successfully wrote {len(data)} records to {self.database}.{self.table}"
            )
        except Exception as e:
            logger.error(f"Failed to write to ClickHouse: {e}")
            raise e

    async def disconnect(self) -> None:
        """Disconnect from ClickHouse."""
        if self.client:
            try:
                self.client.close()
                logger.info("Disconnected from ClickHouse")
            except Exception as e:
                logger.error(f"Error disconnecting from ClickHouse: {e}")
            finally:
                self.client = None
