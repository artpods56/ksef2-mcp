from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

from ksef2.domain.models.permissions import (
    EntityRole,
    EntityRolesResponse,
    EntityRoleType,
)

from ksef2_mcp.config import AppSettings
from ksef2_mcp.services.authenticated_client import AuthenticatedClientFactory
from ksef2_mcp.services.permissions import PermissionService


def test_permission_service_passes_pagination_to_sdk() -> None:
    captured: dict[str, object] = {}
    expected_response = EntityRolesResponse(
        roles=[
            EntityRole(
                role=cast(EntityRoleType, "court_bailiff"),
                description="Court bailiff role",
                start_date=datetime.now(UTC),
            )
        ],
        has_more=False,
    )

    class StubPermissionsApi:
        def get_entity_roles(self, *, params):
            captured["page_offset"] = params.page_offset
            captured["page_size"] = params.page_size
            return expected_response

    class StubFactory:
        @contextmanager
        def create(self):
            yield SimpleNamespace(permissions=StubPermissionsApi())

    service = PermissionService(
        client_factory=cast(AuthenticatedClientFactory, StubFactory()),
        settings=AppSettings(nip="5261040828"),
    )

    result = service.list_permissions(page_offset=2, page_size=10)

    assert result == expected_response
    assert captured == {"page_offset": 2, "page_size": 10}
