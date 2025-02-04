"""Definition of source streams."""

from .coinbase_source import CoinbaseSource
from .source import Source, get_source

__all__ = ["CoinbaseSource", "Source", "get_source"]
