from datetime import datetime
from typing import Any
from uuid import UUID

from ksef2_mcp.domain.common import ContractModel
from ksef2_mcp.domain.enums import InvoiceStatus, SubmissionStatus
from ksef2_mcp.domain.models import InvoiceBuilderStep


class UploadInvoiceXmlResult(ContractModel):
    invoice_id: str
    status: InvoiceStatus


class InvoiceListItem(ContractModel):
    invoice_id: str
    status: InvoiceStatus
    created_at: datetime
    updated_at: datetime
    latest_submission_id: str | None = None


class ListInvoicesResult(ContractModel):
    invoices: list[InvoiceListItem]


class InvoiceDocumentResult(ContractModel):
    invoice_id: str
    status: InvoiceStatus
    invoice_xml: str
    created_at: datetime
    updated_at: datetime
    latest_submission_id: str | None = None


class SubmissionResult(ContractModel):
    invoice_id: str
    submission_id: str
    status: SubmissionStatus
    ksef_number: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None


class InvoiceBuilderHandleResult(ContractModel):
    uuid: UUID
    completed_steps: list[InvoiceBuilderStep]
    missing_steps: list[InvoiceBuilderStep]
    is_ready_to_build: bool


class InvoiceDownloadLinkResult(ContractModel):
    download_id: str
    download_url: str
    file_name: str
    file_path: str
    media_type: str
