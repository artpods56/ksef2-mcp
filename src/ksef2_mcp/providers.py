from __future__ import annotations

import uuid
from typing import Mapping

from .contracts import (
    CheckInvoiceStatusGatewayResult,
    RequestContext,
    SendInvoiceGatewayResult,
)


class HeaderContextResolver:
    """Resolves request context from incoming metadata headers."""

    def resolve(self, metadata: Mapping[str, str] | None = None) -> RequestContext:
        request_metadata = metadata or {}
        capabilities_header = request_metadata.get("x-capabilities", "")
        capabilities = frozenset(capability.strip() for capability in capabilities_header.split(",") if capability.strip())
        return RequestContext(
            user_id=request_metadata.get("x-user-id", "anonymous"),
            workspace_id=request_metadata.get("x-workspace-id", "default"),
            capabilities=capabilities,
            correlation_id=request_metadata.get("x-correlation-id", str(uuid.uuid4())),
        )


class InMemoryKsefGateway:
    """Temporary gateway stub for local development and tests."""

    def __init__(self) -> None:
        self._operations: dict[str, str] = {}

    def send_invoice(self, *, workspace_id: str, invoice_reference: str) -> SendInvoiceGatewayResult:
        operation_id = f"op-{workspace_id}-{invoice_reference}"
        self._operations[operation_id] = "queued"
        return {
            "operation_id": operation_id,
            "status": "queued",
            "message": "Invoice accepted for processing",
        }

    def check_invoice_status(
        self,
        *,
        workspace_id: str,
        operation_id: str,
    ) -> CheckInvoiceStatusGatewayResult:
        _ = workspace_id
        status = self._operations.get(operation_id, "not_found")
        details = "Operation exists" if status != "not_found" else "Unknown operation"
        return {
            "operation_id": operation_id,
            "status": status,
            "details": details,
        }
