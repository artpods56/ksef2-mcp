from contextlib import contextmanager
from types import SimpleNamespace
from typing import cast

import pytest
from ksef2.domain.models.tokens import GenerateTokenResponse, TokenPermission

from ksef2_mcp.config import AppSettings, KsefAuthMode
from ksef2_mcp.errors import ConfigurationError
from ksef2_mcp.services.authenticated_client import AuthenticatedClientFactory
from ksef2_mcp.services.tokens import LocalTokenService


def test_authenticated_client_factory_requires_xades_paths() -> None:
    with pytest.raises(ConfigurationError, match="XAdES authentication paths"):
        AuthenticatedClientFactory(
            AppSettings(
                auth_mode=KsefAuthMode.XADES,
                nip="5261040828",
                xades_certificate_path=None,
                xades_private_key_path=None,
            )
        )


def test_token_service_delegates_to_authenticated_client() -> None:
    captured: dict[str, object] = {}
    expected_response = cast(GenerateTokenResponse, object())

    class StubTokensApi:
        def generate(self, *, permissions, description):
            captured["permissions"] = permissions
            captured["description"] = description
            return expected_response

    class StubFactory:
        @contextmanager
        def create(self):
            yield SimpleNamespace(tokens=StubTokensApi())

    service = LocalTokenService(
        client_factory=cast(AuthenticatedClientFactory, StubFactory()),
        settings=AppSettings(nip="5261040828"),
    )

    result = service.generate_token(
        permissions=[cast(TokenPermission, "invoice_write")],
        description="Token for tests",
    )

    assert result is expected_response
    assert captured == {
        "permissions": ["invoice_write"],
        "description": "Token for tests",
    }
