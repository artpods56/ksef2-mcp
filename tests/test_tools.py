from ksef2_mcp.tools import register_tools
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


def test_register_tools_registers_all_runtime_tools() -> None:
    registered = []

    class StubApp:
        def add_tool(self, tool):
            registered.append(tool)

    register_tools(StubApp())  # pyright: ignore[reportArgumentType]

    assert registered == [
        list_token_page,
        generate_token,
        revoke_token,
        get_token_status,
        list_permissions,
        open_interactive_session,
        close_interactive_session,
        list_interactive_sessions,
        create_draft,
        get_contexts,
        get_possible_methods,
        update_draft,
        build_draft,
        delete_draft,
    ]
