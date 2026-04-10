from typing import Annotated

from fastmcp.tools.function_tool import tool

from ksef2.domain.models.pagination import TokenListParams
from ksef2.domain.models.tokens import (
    GenerateTokenResponse,
    QueryTokensResponse,
    TokenAuthorIdentifierType,
    TokenPermission,
    TokenStatus,
    TokenStatusResponse,
)

from ksef2_mcp.services.tokens import get_token_service


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


@tool(
    name="revoke_token",
    description="Revoke a KsEF token.",
)
def revoke_token(
    reference_number: Annotated[str, "Reference number of the token to revoke"],
) -> None:
    return get_token_service().revoke_token(
        reference_number=reference_number,
    )


@tool(
    name="list_token_page",
    description="List tokens with optional filters.",
)
def list_token_page(
    status: Annotated[list[TokenStatus] | None, "Filter tokens by status"] = None,
    description: Annotated[str | None, "Filter tokens by description"] = None,
    author_identifier: Annotated[
        str | None, "Filter tokens by author identifier"
    ] = None,
    author_identifier_type: Annotated[
        TokenAuthorIdentifierType | None, "Filter tokens by author identifier type"
    ] = None,
    continuation_token: Annotated[
        str | None, "Continuation token for pagination"
    ] = None,
) -> QueryTokensResponse:
    params = TokenListParams(
        status=status,
        description=description,
        author_identifier=author_identifier,
        author_identifier_type=author_identifier_type,
    )
    return get_token_service().list_token_page(
        params=params,
        continuation_token=continuation_token,
    )


@tool(
    name="get_token_status",
    description="Get the status of a KsEF token.",
)
def get_token_status(
    reference_number: Annotated[str, "Reference number of the token"],
) -> TokenStatusResponse:
    return get_token_service().get_token_status(
        reference_number=reference_number,
    )
