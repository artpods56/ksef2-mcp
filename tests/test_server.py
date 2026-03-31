import asyncio

from ksef2_mcp.config import AppSettings, BackendMode
from ksef2_mcp.server import build_argument_parser, create_server


def test_build_argument_parser_uses_streamable_http_defaults() -> None:
    parser = build_argument_parser()

    args = parser.parse_args([])

    assert args.transport == "streamable-http"
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_create_server_registers_core_tools() -> None:
    async def list_tools():
        server = create_server(AppSettings())
        return await server.list_tools()

    tools = asyncio.run(list_tools())
    tool_names = {tool.name for tool in tools}

    assert "generate_token" in tool_names
    assert "create_invoice_builder" in tool_names
    assert "create_invoice_download_link" in tool_names


def test_create_server_platform_mode_enables_auth_provider() -> None:
    settings = AppSettings(
        backend_mode=BackendMode.PLATFORM,
        required_scopes=["ksef:mcp"],
        platform_access_bindings_json="[]",
    )

    server = create_server(settings)

    assert server.auth is not None


def test_create_server_registers_invoice_download_route() -> None:
    server = create_server(AppSettings())

    routes = server._get_additional_http_routes()
    paths = {route.path for route in routes}

    assert "/downloads/invoices/{download_id}" in paths
