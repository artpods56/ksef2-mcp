from functools import lru_cache
from ksef2.core.exceptions import KSeFApiError, KSeFException
from ksef2.domain.models.pagination import OffsetPaginationParams
from ksef2.domain.models.permissions import EntityRolesResponse
from ksef2_mcp.config import AppSettings, get_app_settings
from ksef2_mcp.errors import KsefMcpError
from ksef2_mcp.services import get_authenticated_client_factory
from ksef2_mcp.services.authenticated_client import AuthenticatedClientFactory


class PermissionService:
    def __init__(
        self,
        client_factory: AuthenticatedClientFactory,
        settings: AppSettings,
    ) -> None:
        self._client_factory = client_factory
        self._settings = settings

    def list_permissions(
        self,
        *,
        params: OffsetPaginationParams,
    ) -> EntityRolesResponse:
        try:
            with self._client_factory.create() as client:
                return client.permissions.get_entity_roles(params=params)
        except KsefMcpError:
            raise
        except KSeFApiError as exc:
            raise KsefMcpError(
                "KSEF_ERROR",
                "KSeF rejected the permission listing request.",
                details={
                    "sdk_code": exc.exception_code.value,
                    "status_code": exc.status_code,
                },
            ) from exc
        except KSeFException as exc:
            raise KsefMcpError(
                "KSEF_ERROR",
                "Permission listing failed in the KSeF SDK.",
                details={"sdk_code": exc.context.get("code")},
            ) from exc


@lru_cache(maxsize=1)
def get_permission_service() -> PermissionService:
    settings = get_app_settings()
    return PermissionService(
        client_factory=get_authenticated_client_factory(),
        settings=settings,
    )
