from functools import lru_cache
from typing import Annotated

from fastmcp.tools.function_tool import tool
from ksef2.domain.models.tokens import GenerateTokenResponse, TokenPermission

from ksef2_mcp.services import TokenService, get_authenticated_client_factory


@lru_cache(maxsize=1)
def get_token_service() -> TokenService:
    return TokenService(get_authenticated_client_factory())


@tool(
    name="generate_token",
    description="Generate a new KsEF token with given permissions.",
)
def generate_token(
    permissions: Annotated[list[TokenPermission], "Permissions to grant to the token"],
    description: Annotated[
        str, "Description of the token"
    ] = "Token for testing purposes",
) -> GenerateTokenResponse:
    return get_token_service().generate_token(
        permissions=permissions,
        description=description,
    )
