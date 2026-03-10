from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .application import WorkflowService
from .contracts import CheckInvoiceStatusInput, SendInvoiceInput
from .domain import (
    CheckInvoiceStatusPayload,
    DiagnoseContextAccessPayload,
    SendInvoicePayload,
)
from .providers import HeaderContextResolver, InMemoryKsefGateway


def build_server() -> FastMCP:
    resolver = HeaderContextResolver()
    service = WorkflowService(gateway=InMemoryKsefGateway())

    server = FastMCP(name="ksef2-mcp")

    @server.tool(description="Send an invoice to KSeF and return an operation handle")
    def send_invoice(invoice_reference: str) -> SendInvoicePayload:
        ctx = resolver.resolve()
        result = service.send_invoice(ctx, SendInvoiceInput(invoice_reference=invoice_reference))
        return result.to_payload()

    @server.tool(description="Check invoice operation status using operation handle")
    def check_invoice_status(operation_id: str) -> CheckInvoiceStatusPayload:
        ctx = resolver.resolve()
        result = service.check_invoice_status(ctx, CheckInvoiceStatusInput(operation_id=operation_id))
        return result.to_payload()

    @server.tool(description="Diagnose resolved user/workspace context and capabilities")
    def diagnose_context_access() -> DiagnoseContextAccessPayload:
        ctx = resolver.resolve()
        result = service.diagnose_context_access(ctx)
        return result.to_payload()

    return server
