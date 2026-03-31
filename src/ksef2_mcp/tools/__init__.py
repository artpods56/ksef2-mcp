from fastmcp import FastMCP

from ksef2_mcp.tools.builder import (
    add_invoice_body,
    add_invoice_entity,
    add_invoice_header,
    add_invoice_line,
    build_invoice_xml,
    create_invoice_builder,
    create_invoice_download_link,
    get_invoice_builder_handle,
)
from ksef2_mcp.tools.permissions import list_permissions
from ksef2_mcp.tools.sessions import (
    close_interactive_session,
    list_interactive_sessions,
    open_interactive_session,
)
from ksef2_mcp.tools.tokens import (
    generate_token,
    get_token_status,
    list_token_page,
    revoke_token,
)


def register_tools(app: FastMCP) -> None:
    # --- tokens tools ---
    app.add_tool(list_token_page)
    app.add_tool(generate_token)
    app.add_tool(revoke_token)
    app.add_tool(get_token_status)

    app.add_tool(list_permissions)
    app.add_tool(open_interactive_session)
    app.add_tool(close_interactive_session)
    app.add_tool(list_interactive_sessions)

    # --- invoice builder tools ---
    app.add_tool(create_invoice_builder)
    app.add_tool(get_invoice_builder_handle)
    app.add_tool(add_invoice_header)
    app.add_tool(add_invoice_entity)
    app.add_tool(add_invoice_line)
    app.add_tool(add_invoice_body)
    app.add_tool(build_invoice_xml)
    app.add_tool(create_invoice_download_link)
