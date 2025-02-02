"""Command line tool listens to a stream and pushes the result to clickhouse.

Raises:
    ValueError: If the URL argument is not a valid URL.
    ValueError: If the config file is not found.

"""

import click
from pathlib import Path
from urllib.parse import urlparse
from urllib.parse import (
    ParseResult,
)  # noqa: F401 # URLType.convert is used by click's type system


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
    type=click.File("r"),
    help="Path to configuration file",
    required=True,
)
@click.option("--url", "-u", type=URLType(), help="URL to connect to", required=True)
def listen(config: click.File, url: ParseResult) -> tuple[Path, ParseResult]:
    """Listen to a stream using the configuration in 'config' and the URL in 'url'.

    Args:
        config (file): Opened file stream of the configuration file
        url (str): Validated URL string
    """
    return (config.name, url)


if __name__ == "__main__":
    listen()
