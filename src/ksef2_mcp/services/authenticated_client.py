import abc
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache, cached_property

from cryptography.x509 import Certificate
from ksef2 import Client, Environment
from ksef2.clients.authenticated import AuthenticatedClient
from ksef2.core.exceptions import (
    KSeFAuthError,
    KSeFUnsupportedEnvironmentError,
    NoCertificateAvailableError,
)
from ksef2.core.xades import (
    XAdESPrivateKey,
    load_certificate_from_pem,
    load_private_key_from_pem,
)

from ksef2_mcp.config import (
    AppSettings,
    BackendMode,
    KsefAuthMode,
    get_app_settings,
)
from ksef2_mcp.errors import AuthenticationError, ConfigurationError


@dataclass(frozen=True)
class TokenCredentials:
    nip: str
    token: str


@dataclass(frozen=True)
class XadesCredentials:
    nip: str
    certificate: Certificate
    private_key: XAdESPrivateKey


class NipProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def nip(self) -> str: ...


class TokenCredentialsProvider(abc.ABC):
    @abc.abstractmethod
    def get_token_credentials(self) -> TokenCredentials: ...


class XadesCredentialsProvider(abc.ABC):
    @abc.abstractmethod
    def get_xades_credentials(self) -> XadesCredentials: ...


class LocalNipProvider(NipProvider):
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    @cached_property
    def nip(self) -> str:
        if self._settings.nip is None:
            raise ConfigurationError("NIP has not been configured.")
        return self._settings.nip


class LocalTokenCredentialsProvider(TokenCredentialsProvider):
    def __init__(self, settings: AppSettings, nip_provider: NipProvider) -> None:
        self._settings = settings
        self._nip_provider = nip_provider

    @cached_property
    def _token(self) -> str:
        if self._settings.ksef_token is None:
            raise ConfigurationError("KSeF token is not configured.")
        return self._settings.ksef_token.get_secret_value()

    def get_token_credentials(self) -> TokenCredentials:
        return TokenCredentials(
            nip=self._nip_provider.nip,
            token=self._token,
        )


class LocalXadesCredentialsProvider(XadesCredentialsProvider):
    def __init__(self, settings: AppSettings, nip_provider: NipProvider) -> None:
        self._settings = settings
        self._nip_provider = nip_provider

    @cached_property
    def _certificate(self) -> Certificate:
        if self._settings.xades_certificate_path is None:
            raise ConfigurationError("XAdES certificate path is not configured.")

        try:
            with open(self._settings.xades_certificate_path, "rb") as file:
                return load_certificate_from_pem(file.read())
        except OSError as exc:
            raise ConfigurationError(
                f"Failed to read XAdES certificate file: {exc}"
            ) from exc
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to parse XAdES certificate: {exc}"
            ) from exc

    @cached_property
    def _private_key(self) -> XAdESPrivateKey:
        if self._settings.xades_private_key_path is None:
            raise ConfigurationError("XAdES private key path is not configured.")

        password = (
            self._settings.xades_private_key_password.get_secret_value().encode("utf-8")
            if self._settings.xades_private_key_password
            else None
        )

        try:
            with open(self._settings.xades_private_key_path, "rb") as file:
                return load_private_key_from_pem(file.read(), password=password)
        except OSError as exc:
            raise ConfigurationError(
                f"Failed to read XAdES private key file: {exc}"
            ) from exc
        except Exception as exc:
            raise ConfigurationError(
                f"Failed to load XAdES private key: {exc}"
            ) from exc

    def get_xades_credentials(self) -> XadesCredentials:
        return XadesCredentials(
            nip=self._nip_provider.nip,
            certificate=self._certificate,
            private_key=self._private_key,
        )


class Authenticator:
    def __init__(
        self,
        *,
        settings: AppSettings,
        nip_provider: NipProvider,
        token_provider: TokenCredentialsProvider,
        xades_provider: XadesCredentialsProvider,
    ) -> None:
        self._settings = settings
        self._nip_provider = nip_provider
        self._token_provider = token_provider
        self._xades_provider = xades_provider

    def with_token(self, *, client: Client) -> AuthenticatedClient:
        credentials = self._token_provider.get_token_credentials()
        return client.authentication.with_token(
            ksef_token=credentials.token,
            nip=credentials.nip,
        )

    def with_xades(self, *, client: Client) -> AuthenticatedClient:
        credentials = self._xades_provider.get_xades_credentials()
        return client.authentication.with_xades(
            nip=credentials.nip,
            cert=credentials.certificate,
            private_key=credentials.private_key,  # pyright: ignore[reportArgumentType] [TODO: fix type issue]
            verify_chain=self._settings.xades_verify_chain,
        )

    def with_test_certificate(self, *, client: Client) -> AuthenticatedClient:
        return client.authentication.with_test_certificate(
            nip=self._nip_provider.nip,
        )


class AuthenticatedClientFactory:
    def __init__(
        self,
        *,
        authenticator: Authenticator,
        auth_mode: KsefAuthMode,
        environment: Environment,
    ) -> None:
        self._authenticator = authenticator
        self._auth_mode = auth_mode
        self._environment = environment

    @contextmanager
    def create(self) -> Generator[AuthenticatedClient, None, None]:
        client = Client(environment=self._environment)

        try:
            match self._auth_mode:
                case KsefAuthMode.TEST_CERTIFICATE:
                    yield self._authenticator.with_test_certificate(client=client)
                case KsefAuthMode.TOKEN:
                    yield self._authenticator.with_token(client=client)
                case KsefAuthMode.XADES:
                    yield self._authenticator.with_xades(client=client)
                case _ as unreachable:
                    assert_never(unreachable)
        except ConfigurationError:
            raise
        except KSeFUnsupportedEnvironmentError as exc:
            raise ConfigurationError(str(exc)) from exc
        except (KSeFAuthError, NoCertificateAvailableError) as exc:
            raise AuthenticationError(
                "Failed to authenticate with KSeF.",
                details={"reason": str(exc)},
            ) from exc
        finally:
            client.close()


@cache
def get_authenticated_client_factory() -> AuthenticatedClientFactory:
    settings = get_app_settings()

    match settings.backend_mode:
        case BackendMode.STANDALONE:
            nip_provider = LocalNipProvider(settings)
            token_provider = LocalTokenCredentialsProvider(
                settings=settings,
                nip_provider=nip_provider,
            )
            xades_provider = LocalXadesCredentialsProvider(
                settings=settings,
                nip_provider=nip_provider,
            )
        case BackendMode.PLATFORM:
            raise NotImplementedError("Platform backend mode is not supported yet.")
        case _ as unreachable:
            assert_never(unreachable)

    authenticator = Authenticator(
        settings=settings,
        nip_provider=nip_provider,
        token_provider=token_provider,
        xades_provider=xades_provider,
    )

    return AuthenticatedClientFactory(
        authenticator=authenticator,
        auth_mode=settings.auth_mode,
        environment=settings.environment,
    )
