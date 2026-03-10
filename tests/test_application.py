from ksef2_mcp.application import PolicyError, WorkflowService
from ksef2_mcp.contracts import CheckInvoiceStatusInput, RequestContext, SendInvoiceInput
from ksef2_mcp.domain import CheckInvoiceStatusResponse, SendInvoiceResponse
from ksef2_mcp.providers import InMemoryKsefGateway


def _ctx(*caps: str) -> RequestContext:
    return RequestContext(
        user_id="user-1",
        workspace_id="ws-1",
        capabilities=frozenset(caps),
        correlation_id="corr-1",
    )


def test_send_invoice_requires_capability() -> None:
    service = WorkflowService(gateway=InMemoryKsefGateway())

    try:
        service.send_invoice(_ctx(), SendInvoiceInput(invoice_reference="INV-1"))
    except PolicyError:
        pass
    else:
        raise AssertionError("Expected PolicyError when capability is missing")


def test_send_invoice_and_status_flow() -> None:
    service = WorkflowService(gateway=InMemoryKsefGateway())

    sent = service.send_invoice(_ctx("send_invoice"), SendInvoiceInput(invoice_reference="INV-1"))
    status = service.check_invoice_status(
        _ctx("check_invoice_status"),
        CheckInvoiceStatusInput(operation_id=sent.operation_id),
    )

    assert isinstance(sent, SendInvoiceResponse)
    assert isinstance(status, CheckInvoiceStatusResponse)
    assert sent.status == "queued"
    assert status.status == "queued"
