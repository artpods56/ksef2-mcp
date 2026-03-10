from __future__ import annotations

from argparse import ArgumentParser
from importlib.metadata import version
from typing import Any

from ksef2 import Client, Environment, FormSchema
from mcp.server.fastmcp import FastMCP


def parse_environment(value: str) -> Environment:
    normalized = value.strip().upper()
    try:
        return Environment[normalized]
    except KeyError as exc:
        supported = ", ".join(environment.name for environment in Environment)
        raise ValueError(
            f"Unsupported environment {value!r}. Choose one of: {supported}."
        ) from exc


def available_client_features(environment: Environment) -> list[str]:
    client = Client(environment)
    try:
        features = []
        for name in ("authentication", "encryption", "peppol"):
            getattr(client, name)
            features.append(name)
        if environment is Environment.TEST:
            client.testdata
            features.append("testdata")
        return features
    finally:
        client.close()


def sdk_overview_payload() -> dict[str, Any]:
    return {
        "ksef2_version": version("ksef2"),
        "mcp_version": version("mcp"),
        "environments": [
            {"name": environment.name, "base_url": environment.value}
            for environment in Environment
        ],
        "form_schemas": [schema.name for schema in FormSchema],
    }


def environment_summary_payload(environment_name: str) -> dict[str, Any]:
    environment = parse_environment(environment_name)
    return {
        "environment": environment.name,
        "base_url": environment.value,
        "client_features": available_client_features(environment),
        "supports_testdata": environment is Environment.TEST,
    }


mcp = FastMCP(
    "ksef2-mcp",
    instructions=(
        "Use these tools to inspect the installed ksef2 SDK and the KSeF "
        "environments it supports. Extend this server with authenticated "
        "invoice and session workflows as needed."
    ),
)


@mcp.tool()
def sdk_overview() -> dict[str, Any]:
    """Return the installed SDK versions plus supported environments and forms."""
    return sdk_overview_payload()


@mcp.tool()
def describe_environment(environment: str = "TEST") -> dict[str, Any]:
    """Describe the selected KSeF environment and top-level ksef2 client features."""
    return environment_summary_payload(environment)


@mcp.resource("ksef2://setup")
def setup_resource() -> str:
    return (
        "This server depends on the published ksef2 package. "
        "Start with sdk_overview() to inspect the installed SDK, then "
        "describe_environment(environment='TEST') to confirm the target KSeF "
        "environment before adding authenticated workflows."
    )


def build_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the ksef2 MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="MCP transport to expose.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host used for HTTP transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port used for HTTP transports.",
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    if args.transport != "stdio":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
    mcp.run(args.transport)


if __name__ == "__main__":
    main()
