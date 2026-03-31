from ksef2_mcp.config import AppSettings, BackendMode
from ksef2_mcp.errors import PlatformError


def ensure_standalone_backend(settings: AppSettings, *, tool_name: str) -> None:
    if settings.backend_mode is BackendMode.STANDALONE:
        return

    raise PlatformError(
        f"{tool_name} is not implemented for platform mode yet.",
        details={"backend_mode": settings.backend_mode.value, "tool_name": tool_name},
    )
