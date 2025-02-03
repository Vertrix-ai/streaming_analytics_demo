"""Command line tool listens to a stream and pushes the result to clickhouse.

Raises:
    ValueError: If the URL argument is not a valid URL.
    ValueError: If the config file is not found.

"""

import click
import json
import logging
from jsonschema import validate, ValidationError
from pathlib import Path
from typing import Dict
import yaml

from streaming_analytics_demo.sinks import FileSink
from streaming_analytics_demo.sources import CoinbaseSource

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
    required=True,
)
def listen(config: Path) -> tuple[Path]:
    """Listen to a stream using the configuration in 'config'."""
    import asyncio

    async def run():
        config_data = build_config(config)
        source = await _async_connect_source(config_data)
        sink = await _async_connect_sink(config_data)
        await _async_listen(source, sink)

    asyncio.run(run())


async def _async_connect_source(config_data: Dict) -> CoinbaseSource:
    """Async implementation of listen command."""
    source_config = config_data.get("source")
    source = CoinbaseSource(source_config)
    try:
        logger.info("Connecting to Coinbase WebSocket feed")
        await source.connect()
        logger.info("Connected to Coinbase WebSocket feed")
    except ConnectionError as e:
        logger.error("Failed to connect to Coinbase WebSocket feed: {}", e)
        raise click.BadParameter(f"Failed to connect to Coinbase WebSocket feed: {e}")
    return source


async def _async_connect_sink(config_data: Dict) -> FileSink:
    """Async implementation of listen command."""
    sink_config = config_data.get("sink")
    sink = FileSink(sink_config)
    await sink.connect()
    return sink


async def _async_listen(source: CoinbaseSource, sink: FileSink) -> None:
    """Async implementation of listen command."""
    try:
        while True:
            try:
                message = await source.receive()
                logger.debug("Received message: %s", message)
                await sink.write(json.dumps(message))
            except KeyboardInterrupt:
                logger.info("Received interrupt, shutting down...")
                break
            except Exception as e:
                logger.error("Error processing message: %s", str(e))
                break
    except Exception as e:
        logger.error("lost connection to feed: %s", str(e))
        raise e
    finally:
        logger.info("Disconnecting from Coinbase WebSocket feed")
        await source.disconnect()
        await sink.disconnect()


def build_config(config_path: Path) -> dict:
    """Build a configuration dictionary from config file.

    Args:
        config_path (Path): Path to the configuration file

    Returns:
        dict: Parsed configuration dictionary

    Raises:
        click.BadParameter: If the YAML is invalid, schema validation fails, or file cannot be read
    """
    try:
        # Load schema
        schema_path = CoinbaseSource.get_schema_path()
        logger.info("Loading schema from: %s", str(schema_path))
        with open(schema_path, "r") as f:
            schema = yaml.safe_load(f)

        # Load config
        logger.info("Loading config from: %s", str(config_path))
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate against schema
        logger.info("Validating config against schema")
        validate(instance=config, schema=schema)
        logger.info("Config validation passed")
        return config

    except yaml.YAMLError as e:
        logger.error("Invalid YAML in config file: %s", str(e))
        raise click.BadParameter(f"Invalid YAML in config file: {e}")
    except ValidationError as e:
        logger.error("Config validation failed: %s", e.message)
        raise click.BadParameter(f"Config validation failed: {e.message}")
    except Exception as e:
        logger.error("Error reading config file: %s", str(e))
        raise click.BadParameter(f"Error reading config file: {e}")


if __name__ == "__main__":
    listen()
