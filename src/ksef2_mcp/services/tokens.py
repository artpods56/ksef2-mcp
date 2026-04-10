import abc
from functools import lru_cache

from ksef2.core.exceptions import KSeFApiError, KSeFException
from ksef2.domain.models.pagination import TokenListParams
from ksef2.domain.models.tokens import (
    GenerateTokenResponse,
    TokenPermission,
    TokenStatusResponse,
    QueryTokensResponse,
)

from ksef2_mcp.config import get_app_settings
from ksef2_mcp.errors import ErrorCode, KsefMcpError
from ksef2_mcp.services.authenticated_client import (
    AuthenticatedClientFactory,
    get_authenticated_client_factory,
)


class BaseTokenService(abc.ABC):
    def __init__(self, client_factory: AuthenticatedClientFactory) -> None:
        self._client_factory = client_factory

    @abc.abstractmethod
    def generate_token(
        self,
        *,
        permissions: list[TokenPermission],
        description: str,
    ) -> GenerateTokenResponse:
        raise NotImplementedError


class LocalTokenService(BaseTokenService):
    def __init__(
        self,
        client_factory: AuthenticatedClientFactory,
    ) -> None:
        super().__init__(client_factory=client_factory)

    def generate_token(
        self,
        *,
        permissions: list[TokenPermission],
        description: str,
    ) -> GenerateTokenResponse:
        try:
            with self._client_factory.create() as client:
                return client.tokens.generate(
                    permissions=permissions,
                    description=description,
                )
        except KsefMcpError:
            raise
        except KSeFApiError as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "KSeF rejected the token generation request.",
                details={
                    "sdk_code": exc.exception_code.value,
                    "status_code": exc.status_code,
                },
            ) from exc
        except KSeFException as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "Token generation failed in the KSeF SDK.",
                details={"sdk_code": exc.context.get("code")},
            ) from exc

    def list_token_page(
        self,
        params: TokenListParams,
        continuation_token: str | None = None,
    ) -> QueryTokensResponse:
        try:
            with self._client_factory.create() as client:
                return client.tokens.list_page(
                    params=params, continuation_token=continuation_token
                )
        except KsefMcpError:
            raise

    def get_token_status(self, reference_number: str) -> TokenStatusResponse:
        try:
            with self._client_factory.create() as client:
                return client.tokens.status(reference_number=reference_number)
        except KsefMcpError:
            raise
        except KSeFApiError as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "KSeF rejected the token status request.",
                details={
                    "sdk_code": exc.exception_code.value,
                    "status_code": exc.status_code,
                },
            ) from exc
        except KSeFException as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "Token status request failed in the KSeF SDK.",
                details={"sdk_code": exc.context.get("code")},
            ) from exc

    def revoke_token(self, reference_number: str) -> None:
        try:
            with self._client_factory.create() as client:
                client.tokens.revoke(reference_number=reference_number)
        except KsefMcpError:
            raise
        except KSeFApiError as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "KSeF rejected the token revocation request.",
                details={
                    "sdk_code": exc.exception_code.value,
                    "status_code": exc.status_code,
                },
            ) from exc
        except KSeFException as exc:
            raise KsefMcpError(
                ErrorCode.KSEF_ERROR,
                "Token revocation failed in the KSeF SDK.",
                details={"sdk_code": exc.context.get("code")},
            ) from exc


@lru_cache(maxsize=1)
def get_token_service() -> LocalTokenService:
    settings = get_app_settings()
    return LocalTokenService(
        client_factory=get_authenticated_client_factory(),
    )
