from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Capability(StrEnum):
    UPLOAD_INVOICE_XML = "upload_invoice_xml"
    LIST_INVOICES = "list_invoices"
    GET_INVOICE = "get_invoice"
    SEND_INVOICE = "send_invoice"
    GET_SUBMISSION_STATUS = "get_submission_status"
    EXPORT_INVOICES = "export_invoices"
    GET_EXPORT_STATUS = "get_export_status"
    DOWNLOAD_EXPORT_PACKAGE = "download_export_package"
    LIST_PERMISSIONS = "list_permissions"
    GENERATE_TOKEN = "generate_token"
    GET_OPERATION_STATUS = "get_operation_status"
    CHECK_INVOICE_STATUS = "check_invoice_status"


class OperationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolContextDTO(ContractModel):
    correlation_id: str
    tool_name: str
    backend_mode: str
    workspace_id: str
    user_id: str
    client_id: str | None = None
    environment: str | None = None
    capabilities: list[str]


class ArtifactMetadata(ContractModel):
    saved_files: list[str] = Field(default_factory=list)
    media_type: str | None = None
