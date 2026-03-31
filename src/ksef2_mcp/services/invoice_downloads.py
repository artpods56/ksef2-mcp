import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from ksef2.services.renderers import InvoicePDFExporter

from ksef2_mcp.config import AppSettings, get_app_settings
from ksef2_mcp.domain.outputs import InvoiceDownloadLinkResult
from ksef2_mcp.errors import ResourceNotFoundError
from ksef2_mcp.services.builder import LocalInvoiceBuilderService, get_builder_service

DOWNLOAD_ROUTE_PREFIX = "/downloads/invoices"
_DEFAULT_MEDIA_TYPE = "application/xml"
_DOWNLOAD_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
type DownloadFormat = Literal["xml", "pdf"]
_FORMAT_MEDIA_TYPES: dict[DownloadFormat, str] = {
    "xml": "application/xml",
    "pdf": "application/pdf",
}


@dataclass(slots=True)
class InvoiceDownloadArtifact:
    download_id: str
    file_name: str
    file_path: Path
    media_type: str = _DEFAULT_MEDIA_TYPE


_DOWNLOAD_ARTIFACTS: dict[str, InvoiceDownloadArtifact] = {}
class InvoiceDownloadService:
    def __init__(
        self,
        builder_service: LocalInvoiceBuilderService | None = None,
        pdf_exporter: InvoicePDFExporter | None = None,
    ) -> None:
        self._builder_service = builder_service or get_builder_service()
        self._pdf_exporter = pdf_exporter or InvoicePDFExporter()

    def _normalize_file_name(
        self,
        uuid: UUID,
        file_name: str | None,
        file_format: DownloadFormat,
    ) -> str:
        requested_name = (file_name or f"invoice-{uuid}.{file_format}").strip()
        safe_name = Path(requested_name).name
        if not safe_name:
            safe_name = f"invoice-{uuid}.{file_format}"
        if not safe_name.lower().endswith(f".{file_format}"):
            safe_name = f"{safe_name.rsplit('.', 1)[0]}.{file_format}"

        normalized_name = _DOWNLOAD_FILENAME_PATTERN.sub("_", safe_name).strip("._")
        if not normalized_name:
            return f"invoice-{uuid}.{file_format}"
        if not normalized_name.lower().endswith(f".{file_format}"):
            return f"{normalized_name.rsplit('.', 1)[0]}.{file_format}"
        return normalized_name

    def create_invoice_download_link(
        self,
        uuid: UUID,
        *,
        file_format: DownloadFormat = "xml",
        file_name: str | None = None,
        settings: AppSettings | None = None,
    ) -> InvoiceDownloadLinkResult:
        resolved_settings = settings or get_app_settings()
        invoice_xml = self._builder_service.build_invoice(uuid)

        download_id = str(uuid4())
        normalized_file_name = self._normalize_file_name(
            uuid,
            file_name,
            file_format,
        )
        export_directory = (
            resolved_settings.default_export_directory / "invoice-downloads"
        ).resolve()
        export_directory.mkdir(parents=True, exist_ok=True)

        file_path = export_directory / f"{download_id}-{normalized_file_name}"
        match file_format:
            case "xml":
                file_path.write_text(invoice_xml, encoding="utf-8")
            case "pdf":
                file_path.write_bytes(self._pdf_exporter.export_from_string(invoice_xml))
            case _:
                raise ValueError(f"Unsupported file format: {file_format!r}")

        artifact = InvoiceDownloadArtifact(
            download_id=download_id,
            file_name=normalized_file_name,
            file_path=file_path,
            media_type=_FORMAT_MEDIA_TYPES[file_format],
        )
        _DOWNLOAD_ARTIFACTS[download_id] = artifact

        base_url = str(resolved_settings.resource_server_url).rstrip("/")
        return InvoiceDownloadLinkResult(
            download_id=download_id,
            download_url=f"{base_url}{DOWNLOAD_ROUTE_PREFIX}/{download_id}",
            file_name=artifact.file_name,
            file_path=str(artifact.file_path),
            media_type=artifact.media_type,
        )

    def get_artifact_or_raise(self, download_id: str) -> InvoiceDownloadArtifact:
        artifact = _DOWNLOAD_ARTIFACTS.get(download_id)
        if artifact is None or not artifact.file_path.exists():
            raise ResourceNotFoundError(
                f"No downloadable invoice export with id {download_id!r} was found."
            )
        return artifact


def get_invoice_download_service() -> InvoiceDownloadService:
    return InvoiceDownloadService()
