from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    FEATURE_NOT_ENABLED = "FEATURE_NOT_ENABLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    KSEF_AUTH_FAILED = "KSEF_AUTH_FAILED"
    KSEF_ERROR = "KSEF_ERROR"
    KSEF_SESSION_EXPIRED = "KSEF_SESSION_EXPIRED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    PLATFORM_ERROR = "PLATFORM_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_NOT_READY = "RESOURCE_NOT_READY"
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    INVOICE_BUILDER_ERROR = "INVOICE_BUILDER_ERROR"


class KsefMcpError(Exception):
    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code.value if isinstance(code, ErrorCode) else str(code)
        self.message = message
        self.details = details
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ConfigurationError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.CONFIGURATION_ERROR, message, details=details)


class AuthenticationError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.KSEF_AUTH_FAILED, message, details=details)


class InvalidInputError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.INVALID_INPUT, message, details=details)


class ResourceNotFoundError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.RESOURCE_NOT_FOUND, message, details=details)


class SessionExpiredError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.KSEF_SESSION_EXPIRED, message, details=details)


class SessionManagementError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.KSEF_ERROR, message, details=details)


class OperationTimeoutError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.OPERATION_TIMEOUT, message, details=details)


class PlatformError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.PLATFORM_ERROR, message, details=details)


class InvoiceBuilderError(KsefMcpError):
    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(ErrorCode.INVOICE_BUILDER_ERROR, message, details=details)
