"""Sinks for the streaming analytics demo."""

from .file_sink import FileSink
from .clickhouse_sink import ClickHouseConnectSink
from .sink import Sink, get_sink, register_sink

__all__ = ["FileSink", "Sink", "get_sink", "register_sink", "ClickHouseConnectSink"]
