from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class SendInvoicePayload(TypedDict):
    operation_id: str
    status: str
    message: str


class CheckInvoiceStatusPayload(TypedDict):
    operation_id: str
    status: str
    details: str


class DiagnoseContextAccessPayload(TypedDict):
    user_id: str
    workspace_id: str
    correlation_id: str
    capabilities: list[str]


@dataclass(frozen=True)
class SendInvoiceResponse:
    operation_id: str
    status: str
    message: str

    def to_payload(self) -> SendInvoicePayload:
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "message": self.message,
        }


@dataclass(frozen=True)
class CheckInvoiceStatusResponse:
    operation_id: str
    status: str
    details: str

    def to_payload(self) -> CheckInvoiceStatusPayload:
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "details": self.details,
        }


@dataclass(frozen=True)
class DiagnoseContextAccessResponse:
    user_id: str
    workspace_id: str
    correlation_id: str
    capabilities: tuple[str, ...]

    def to_payload(self) -> DiagnoseContextAccessPayload:
        return {
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "correlation_id": self.correlation_id,
            "capabilities": list(self.capabilities),
        }
