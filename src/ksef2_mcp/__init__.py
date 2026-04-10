from fastmcp import FastMCP


def create_server(settings=None) -> FastMCP:
    from ksef2_mcp.server import create_server as _create_server

    return _create_server(settings)


def main() -> None:
    from ksef2_mcp.server import main as _main

    _main()


__all__ = ["create_server", "main"]
