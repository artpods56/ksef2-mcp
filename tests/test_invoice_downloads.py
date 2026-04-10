from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from ksef2_mcp.adapters.draft_store import _SHARED_DRAFT_STATES
from ksef2_mcp.config import AppSettings
from ksef2_mcp.server import create_server
from ksef2_mcp.services.drafts import (
    CallOperation,
    DoneOperation,
    DraftRuntimeService,
    SpawnOperation,
)
from ksef2_mcp.services.invoice_downloads import (
    _DOWNLOAD_ARTIFACTS,
    InvoiceDownloadService,
)


@pytest.fixture(autouse=True)
def clear_invoice_download_state() -> None:
    _SHARED_DRAFT_STATES.clear()
    _DOWNLOAD_ARTIFACTS.clear()


def _create_ready_draft() -> tuple[DraftRuntimeService, UUID]:
    service = DraftRuntimeService()
    created = service.create_draft("standard_invoice")
    update = service.update_draft(
        created.draft_id,
        [
            CallOperation(
                context_id="root",
                method="seller",
                args={
                    "name": "Sample Seller Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 1",
                    "tax_id": "5250001001",
                },
            ),
            CallOperation(
                context_id="root",
                method="buyer",
                args={
                    "name": "Sample Buyer Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Klienta 2",
                    "tax_id": "5250001002",
                },
            ),
            SpawnOperation(
                context_id="root",
                method="standard",
                new_context_id="body_1",
            ),
            CallOperation(
                context_id="body_1",
                method="issue_date",
                args={"value": date(2026, 3, 31)},
            ),
            SpawnOperation(
                context_id="body_1",
                method="rows",
                new_context_id="rows_1",
            ),
            CallOperation(
                context_id="rows_1",
                method="add_line",
                args={
                    "name": "Consulting service",
                    "quantity": Decimal("1"),
                    "unit_price_net": Decimal("100.00"),
                    "vat_rate": "23",
                },
            ),
            DoneOperation(
                context_id="rows_1",
                method="done",
            ),
            DoneOperation(
                context_id="body_1",
                method="done",
            ),
        ],
    )
    assert all(operation.status == "succeeded" for operation in update.operations)
    return service, created.draft_id


def test_create_invoice_download_link_saves_xml_and_returns_absolute_url(
    tmp_path: Path,
) -> None:
    draft_runtime_service, draft_id = _create_ready_draft()
    download_service = InvoiceDownloadService(
        draft_runtime_service=draft_runtime_service
    )
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://downloads.example",
    )

    result = download_service.create_invoice_download_link(
        draft_id=draft_id,
        file_name="March invoice",
        settings=settings,
    )

    saved_file = Path(result.file_path)
    assert result.download_url == (
        f"http://downloads.example/downloads/invoices/{result.download_id}"
    )
    assert result.file_name == "March_invoice.xml"
    assert saved_file.is_file()
    assert "Sample Seller Sp. z o.o." in saved_file.read_text(encoding="utf-8")


def test_create_invoice_download_link_saves_pdf_when_requested(tmp_path: Path) -> None:
    draft_runtime_service, draft_id = _create_ready_draft()

    class StubPdfExporter:
        def export_from_string(self, invoice_xml: str) -> bytes:
            assert "Sample Seller Sp. z o.o." in invoice_xml
            return b"%PDF-1.7 sample"

    download_service = InvoiceDownloadService(
        draft_runtime_service=draft_runtime_service,
        pdf_exporter=StubPdfExporter(),  # pyright: ignore[reportArgumentType]
    )
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://downloads.example",
    )

    result = download_service.create_invoice_download_link(
        draft_id=draft_id,
        file_format="pdf",
        file_name="March invoice",
        settings=settings,
    )

    saved_file = Path(result.file_path)
    assert result.file_name == "March_invoice.pdf"
    assert result.media_type == "application/pdf"
    assert saved_file.read_bytes() == b"%PDF-1.7 sample"


def test_download_invoice_route_serves_saved_invoice_xml(tmp_path: Path) -> None:
    draft_runtime_service, draft_id = _create_ready_draft()
    download_service = InvoiceDownloadService(
        draft_runtime_service=draft_runtime_service
    )
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://testserver",
    )
    result = download_service.create_invoice_download_link(
        draft_id=draft_id,
        settings=settings,
    )

    app = create_server(settings).http_app(transport="streamable-http")

    with TestClient(app) as client:
        response = client.get(f"/downloads/invoices/{result.download_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "Consulting service" in response.text


def test_download_invoice_route_serves_saved_invoice_pdf(tmp_path: Path) -> None:
    draft_runtime_service, draft_id = _create_ready_draft()

    class StubPdfExporter:
        def export_from_string(self, invoice_xml: str) -> bytes:
            assert "Consulting service" in invoice_xml
            return b"%PDF-1.7 route"

    download_service = InvoiceDownloadService(
        draft_runtime_service=draft_runtime_service,
        pdf_exporter=StubPdfExporter(),  # pyright: ignore[reportArgumentType]
    )
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://testserver",
    )
    result = download_service.create_invoice_download_link(
        draft_id=draft_id,
        file_format="pdf",
        settings=settings,
    )

    app = create_server(settings).http_app(transport="streamable-http")

    with TestClient(app) as client:
        response = client.get(f"/downloads/invoices/{result.download_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content == b"%PDF-1.7 route"
