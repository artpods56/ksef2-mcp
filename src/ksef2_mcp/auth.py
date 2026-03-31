import json
from pathlib import Path
from typing import Protocol

from fastmcp.server.auth import AccessToken, TokenVerifier
from pydantic import BaseModel, ConfigDict

from ksef2_mcp.config import AppSettings
from ksef2_mcp.domain.common import Capability


class AccessBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    client_id: str
    workspace_id: str
    user_id: str
    capabilities: list[Capability]
    environment: str = "TEST"


class AccessBindingResolver(Protocol):
    required_scopes: list[str]

    def resolve(self, token: str) -> AccessBinding | None: ...


class LocalBindingsResolver:
    def __init__(
        self,
        bindings: list[AccessBinding],
        *,
        required_scopes: list[str] | None = None,
    ) -> None:
        self._bindings_by_token = {binding.token: binding for binding in bindings}
        self.required_scopes = required_scopes or []

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "LocalBindingsResolver":
        raw_bindings = settings.platform_access_bindings_json
        if raw_bindings is None and settings.platform_access_bindings_file is not None:
            raw_bindings = Path(settings.platform_access_bindings_file).read_text(
                encoding="utf-8"
            )
        bindings_payload = json.loads(raw_bindings or "[]")
        bindings = [AccessBinding.model_validate(item) for item in bindings_payload]
        return cls(bindings, required_scopes=settings.required_scopes)

    def resolve(self, token: str) -> AccessBinding | None:
        return self._bindings_by_token.get(token)


class PlatformTokenVerifier(TokenVerifier):
    def __init__(
        self,
        resolver: AccessBindingResolver,
        *,
        required_scopes: list[str] | None = None,
    ) -> None:
        super().__init__(required_scopes=required_scopes or resolver.required_scopes)
        self._resolver = resolver

    async def verify_token(self, token: str) -> AccessToken | None:
        binding = self._resolver.resolve(token)
        if binding is None:
            return None
        return AccessToken(
            token=token,
            client_id=binding.client_id,
            scopes=list(self.required_scopes),
            claims={
                "workspace_id": binding.workspace_id,
                "user_id": binding.user_id,
                "environment": binding.environment,
                "capabilities": [
                    capability.value for capability in binding.capabilities
                ],
            },
        )
