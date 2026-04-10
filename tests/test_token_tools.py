import asyncio

from ksef2.domain.models.tokens import TokenPermission
from pydantic import TypeAdapter

from ksef2_mcp.server import create_server
from ksef2_mcp.tools import register_tools
from ksef2_mcp.tools import tokens as tokens_module


def test_token_permission_schema_is_string_enum() -> None:
    schema = TypeAdapter(TokenPermission).json_schema()

    assert schema == {
        "enum": [
            "invoice_read",
            "invoice_write",
            "introspection",
            "credentials_read",
            "credentials_manage",
            "subunit_manage",
            "enforcement_operations",
        ],
        "type": "string",
    }


def test_generate_token_tool_exposes_permission_enum_and_description() -> None:
    async def list_tools():
        mcp = create_server()
        register_tools(mcp)
        return await mcp.list_tools()

    tools = asyncio.run(list_tools())
    generate_token_tool = next(tool for tool in tools if tool.name == "generate_token")
    permission_schema = generate_token_tool.parameters["properties"]["permissions"]

    assert permission_schema["items"]["enum"] == list(
        tokens_module.TOKEN_PERMISSION_VALUES
    )
    assert (
        permission_schema["description"] == tokens_module.TOKEN_PERMISSION_DESCRIPTION
    )
