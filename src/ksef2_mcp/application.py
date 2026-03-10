from __future__ import annotations

from .contracts import CheckInvoiceStatusInput, KsefGateway, RequestContext, SendInvoiceInput
from .domain import (
    CheckInvoiceStatusResponse,
    DiagnoseContextAccessResponse,
    SendInvoiceResponse,
)


class PolicyError(PermissionError):
    """Raised when a workspace policy denies an action."""


class WorkflowService:
    def __init__(self, gateway: KsefGateway) -> None:
        self._gateway = gateway

    def send_invoice(self, ctx: RequestContext, payload: SendInvoiceInput) -> SendInvoiceResponse:
        self._require_capability(ctx, "send_invoice")
        raw = self._gateway.send_invoice(
            workspace_id=ctx.workspace_id,
            invoice_reference=payload.invoice_reference,
        )
        return SendInvoiceResponse(
            operation_id=raw["operation_id"],
            status=raw["status"],
            message=raw["message"],
        )

    def check_invoice_status(
        self,
        ctx: RequestContext,
        payload: CheckInvoiceStatusInput,
    ) -> CheckInvoiceStatusResponse:
        self._require_capability(ctx, "check_invoice_status")
        raw = self._gateway.check_invoice_status(
            workspace_id=ctx.workspace_id,
            operation_id=payload.operation_id,
        )
        return CheckInvoiceStatusResponse(
            operation_id=raw["operation_id"],
            status=raw["status"],
            details=raw["details"],
        )

    def diagnose_context_access(self, ctx: RequestContext) -> DiagnoseContextAccessResponse:
        return DiagnoseContextAccessResponse(
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            correlation_id=ctx.correlation_id,
            capabilities=tuple(sorted(ctx.capabilities)),
        )

    @staticmethod
    def _require_capability(ctx: RequestContext, capability: str) -> None:
        if not ctx.has_capability(capability):
            raise PolicyError(f"Capability '{capability}' is not enabled for this workspace")
