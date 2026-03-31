from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from ksef2 import Environment
from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from ksef2_mcp.domain.common import Capability


class BackendMode(str, Enum):
    STANDALONE = "standalone"
    PLATFORM = "platform"


class KsefAuthMode(str, Enum):
    TEST_CERTIFICATE = "test_certificate"
    TOKEN = "token"
    XADES = "xades"


SUPPORTED_DATABASES = Literal["sqlite", "mysql", "postgres"]


class DatabaseSettings(BaseSettings):
    db_scheme: SUPPORTED_DATABASES
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: str | None = None
    db_name: str | None = None
    db_path: str | None = None  # for sqlite

    @field_validator("db_path", mode="before")
    def validate_sqlite_path(cls, value: str, info: ValidationInfo):
        if "db_scheme" in info.data:
            if not value and info.data["db_scheme"] == "sqlite":
                raise ValueError(
                    "Field "
                    f"`{info.field_name}` must be set with "
                    f"db_scheme=`{info.data['db_scheme']}`"
                )
        return value

    @field_validator(
        "db_user", "db_password", "db_host", "db_port", "db_name", mode="before"
    )
    def validate_network_fields(cls, value: str, info: ValidationInfo):
        if "db_scheme" in info.data:
            if not value and info.data["db_scheme"] != "sqlite":
                raise ValueError(
                    "Field "
                    f"`{info.field_name}` must be set with "
                    f"db_scheme=`{info.data['db_scheme']}`"
                )
        return value

    @property
    def database_uri(self) -> str:
        if self.db_scheme == "sqlite":
            return f"sqlite:///{self.db_path}"
        else:
            return f"{self.db_scheme}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KSEF_MCP_",
        case_sensitive=False,
        extra="ignore",
    )

    backend_mode: BackendMode = Field(
        default=BackendMode.STANDALONE,
        validation_alias=AliasChoices("backend_mode", "deployment_mode", "mode"),
    )
    environment: Environment = Environment.TEST
    auth_mode: KsefAuthMode = KsefAuthMode.TEST_CERTIFICATE
    nip: str | None = None
    ksef_token: SecretStr | None = None
    xades_certificate_path: Path | None = None
    xades_private_key_path: Path | None = None
    xades_private_key_password: SecretStr | None = None
    xades_verify_chain: bool = False
    user_id: str = "standalone-user"
    workspace_id: str = "standalone-workspace"
    capabilities: Annotated[list[Capability], NoDecode] = Field(
        default_factory=lambda: list(Capability),
    )
    default_export_directory: Path = Path("./exports")
    state_db_path: Path = Path("./.ksef2-mcp/state.sqlite3")
    max_invoice_xml_bytes: int = 2_000_000
    platform_base_url: str | None = None
    platform_internal_token: SecretStr | None = None
    platform_timeout_seconds: float = 30.0
    platform_access_bindings_file: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "platform_access_bindings_file",
            "hosted_bindings_file",
        ),
    )
    platform_access_bindings_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "platform_access_bindings_json",
            "hosted_bindings_json",
        ),
    )
    auth_issuer_url: str = "http://127.0.0.1:8000/auth"
    resource_server_url: str = "http://127.0.0.1:8000"
    required_scopes: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value: Environment | str) -> Environment:
        if isinstance(value, Environment):
            return value
        normalized_value = value.strip().upper()
        try:
            return Environment[normalized_value]
        except KeyError:
            return Environment(value)

    @field_validator("capabilities", mode="before")
    @classmethod
    def validate_capabilities(
        cls, value: str | list[Capability] | list[str]
    ) -> list[Capability]:
        if isinstance(value, str):
            return [
                Capability(item.strip()) for item in value.split(",") if item.strip()
            ]
        return [
            item if isinstance(item, Capability) else Capability(item) for item in value
        ]

    @field_validator("required_scopes", mode="before")
    @classmethod
    def validate_required_scopes(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [item.strip() for item in value if item.strip()]


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    return AppSettings()
