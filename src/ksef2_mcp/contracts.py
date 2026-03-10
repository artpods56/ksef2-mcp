from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, TypedDict


class SendInvoiceGatewayResult(TypedDict):
    operation_id: str
    status: str
    message: str


class CheckInvoiceStatusGatewayResult(TypedDict):
    operation_id: str
    status: str
    details: str


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    workspace_id: str
    capabilities: frozenset[str]
    correlation_id: str

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class SendInvoiceInput:
    invoice_reference: str


@dataclass(frozen=True)
class CheckInvoiceStatusInput:
    operation_id: str


class ContextResolver(Protocol):
    def resolve(self, metadata: Mapping[str, str] | None = None) -> RequestContext: ...


class KsefGateway(Protocol):
    def send_invoice(
        self,
        *,
        workspace_id: str,
        invoice_reference: str,
    ) -> SendInvoiceGatewayResult: ...

    def check_invoice_status(
        self,
        *,
        workspace_id: str,
        operation_id: str,
    ) -> CheckInvoiceStatusGatewayResult: ...
