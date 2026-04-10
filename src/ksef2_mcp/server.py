from argparse import ArgumentParser

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from ksef2_mcp.auth import LocalBindingsResolver, PlatformTokenVerifier
from ksef2_mcp.config import AppSettings, BackendMode
from ksef2_mcp.errors import ResourceNotFoundError
from ksef2_mcp.tools import register_tools

def register_http_routes(app: FastMCP) -> None:
    @app.custom_route(
        "/downloads/invoices/{download_id}",
        methods=["GET"],
        include_in_schema=False,
    )
    async def download_invoice_export(request: Request) -> Response:
        from ksef2_mcp.services.invoice_downloads import get_invoice_download_service

        try:
            artifact = get_invoice_download_service().get_artifact_or_raise(
                request.path_params["download_id"]
            )
        except ResourceNotFoundError as exc:
            return JSONResponse(
                {
                    "code": exc.code,
                    "message": exc.message,
                },
                status_code=404,
            )

        return FileResponse(
            artifact.file_path,
            media_type=artifact.media_type,
            filename=artifact.file_name,
        )


def create_server(settings: AppSettings | None = None) -> FastMCP:
    resolved_settings = settings or AppSettings()

    auth = None
    if resolved_settings.backend_mode is BackendMode.PLATFORM:
        auth = PlatformTokenVerifier(
            LocalBindingsResolver.from_settings(resolved_settings),
            required_scopes=resolved_settings.required_scopes,
        )

    mcp = FastMCP(
        "ksef2-mcp",
        instructions=(
            "This is a thin MCP adapter based on ksef2 SDK for KSeF workflows. "
        ),
        auth=auth,
    )

    register_tools(mcp)
    register_http_routes(mcp)

    return mcp


def build_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the ksef2 MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="streamable-http",
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
    mcp = create_server()

    if args.transport != "stdio":
        mcp.run(args.transport, host=args.host, port=args.port)
        return

    mcp.run(args.transport)


__all__ = ["create_server", "main"]
