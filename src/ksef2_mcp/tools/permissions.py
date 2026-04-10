from typing import Annotated
from fastmcp.tools.function_tool import tool
from ksef2.domain.models.pagination import OffsetPaginationParams
from ksef2.domain.models.permissions import EntityRolesResponse
from ksef2_mcp.services.permissions import get_permission_service


@tool(
    name="list_permissions",
    description=(
        "List the entity roles visible for the currently authenticated KSeF context."
    ),
)
def list_permissions(
    page_offset: Annotated[int, "Zero-based results page offset."] = 0,
    page_size: Annotated[int, "Number of roles to return, between 10 and 100."] = 10,
) -> EntityRolesResponse:
    params = OffsetPaginationParams(
        page_offset=page_offset,
        page_size=page_size,
    )
    return get_permission_service().list_permissions(
        params=params,
    )
