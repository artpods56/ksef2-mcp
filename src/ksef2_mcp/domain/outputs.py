from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from ksef2_mcp.domain.common import ContractModel
from ksef2_mcp.domain.enums import InvoiceStatus, SubmissionStatus


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


class InvoiceDownloadLinkResult(ContractModel):
    download_id: str
    download_url: str
    file_name: str
    file_path: str
    media_type: str


class DraftContextResult(ContractModel):
    context_id: str
    builder_type: str
    parent_context_id: str | None = None
    opened_via_method: str | None = None


class DraftMethodResult(ContractModel):
    name: str
    operation_type: str
    payload_schema: dict[str, Any]


class CreateDraftResult(ContractModel):
    draft_id: UUID
    draft_type: str
    root_context_id: str


class DraftContextsResult(ContractModel):
    draft_id: UUID
    draft_type: str
    contexts: list[DraftContextResult] = Field(default_factory=list)


class DraftPossibleMethodsResult(ContractModel):
    draft_id: UUID
    context_id: str
    builder_type: str
    methods: list[DraftMethodResult] = Field(default_factory=list)


class DraftOperationResult(ContractModel):
    op_index: int
    op_id: str | None = None
    op: str
    context_id: str
    method: str
    status: str
    new_context_id: str | None = None
    message: str | None = None
    error_code: str | None = None


class UpdateDraftResult(ContractModel):
    draft_id: UUID
    draft_type: str
    operations: list[DraftOperationResult] = Field(default_factory=list)
    contexts: list[DraftContextResult] = Field(default_factory=list)


class BuildDraftResult(ContractModel):
    draft_id: UUID
    draft_type: str
    output_format: str
    content: Any


class DeleteDraftResult(ContractModel):
    draft_id: UUID
    deleted: bool
