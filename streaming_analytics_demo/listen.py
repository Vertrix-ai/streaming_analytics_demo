"""Command line tool listens to a stream and pushes the result to clickhouse.

Raises:
    ValueError: If the URL argument is not a valid URL.
    ValueError: If the config file is not found.

"""

import click
from jsonschema import validate, ValidationError
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import (
    ParseResult,
)  # noqa: F401 # URLType.convert is used by click's type system
import yaml

from streaming_analytics_demo.sources import CoinbaseSource


class URLType(click.ParamType):
    """Click type for validating URLs."""

    name = "url"

    def convert(self, value, param, ctx) -> ParseResult:
        """Given a string, validate it as a URL.

        Raises:
            ValueError: If the string is not a valid URL.
            ValueError: If the string is empty.

        Returns:
            ParseResult: a parsed URL
        """
        if value is None:
            raise ValueError("URL cannot be empty")

        try:
            result = urlparse(value)
            if all([result.scheme, result.netloc]):
                return result
            raise ValueError
        except ValueError:
            self.fail(f"'{value}' is not a valid URL", param, ctx)


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
    required=True,
)
@click.option("--url", "-u", type=URLType(), help="URL to connect to", required=True)
def listen(config: Path, url: ParseResult) -> tuple[Path, ParseResult]:
    """Listen to a stream using the configuration in 'config' and the URL in 'url'.

    Args:
        config (Path): Path to the configuration file
        url (ParseResult): Validated URL object

    Returns:
        tuple[Path, ParseResult]: Tuple of config path and parsed URL
    """
    config = build_config(config)
    return (config, url)


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
        with open(schema_path, "r") as f:
            schema = yaml.safe_load(f)

        # Load config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate against schema
        validate(instance=config, schema=schema)
        return config

    except yaml.YAMLError as e:
        raise click.BadParameter(f"Invalid YAML in config file: {e}")
    except ValidationError as e:
        raise click.BadParameter(f"Config validation failed: {e.message}")
    except Exception as e:
        raise click.BadParameter(f"Error reading config file: {e}")


if __name__ == "__main__":
    listen()
