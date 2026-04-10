from fastmcp import FastMCP

from ksef2_mcp.tools.drafts import (
    build_draft,
    create_draft,
    delete_draft,
    get_contexts,
    get_possible_methods,
    update_draft,
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

    # --- draft runtime tools ---
    app.add_tool(create_draft)
    app.add_tool(get_contexts)
    app.add_tool(get_possible_methods)
    app.add_tool(update_draft)
    app.add_tool(build_draft)
    app.add_tool(delete_draft)
