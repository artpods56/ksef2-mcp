from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from starlette.testclient import TestClient

from ksef2_mcp.adapters.uow import _SHARED_IN_MEMORY_STORE
from ksef2_mcp.config import AppSettings
from ksef2_mcp.server import create_server
from ksef2_mcp.services.builder import LocalInvoiceBuilderService
from ksef2_mcp.services.invoice_downloads import (
    _DOWNLOAD_ARTIFACTS,
    InvoiceDownloadService,
)


@pytest.fixture(autouse=True)
def clear_invoice_download_state() -> None:
    _SHARED_IN_MEMORY_STORE["sessions"].clear()
    _SHARED_IN_MEMORY_STORE["builders"].clear()
    _DOWNLOAD_ARTIFACTS.clear()


def _create_ready_builder() -> tuple[LocalInvoiceBuilderService, UUID]:
    service = LocalInvoiceBuilderService()
    handle = service.create_invoice_builder()

    service.add_entity(
        uuid=handle.uuid,
        entity_type="seller",
        name="Sample Seller Sp. z o.o.",
        country_code="PL",
        address_line_1="ul. Prosta 1",
        tax_id="5250001001",
    )
    service.add_entity(
        uuid=handle.uuid,
        entity_type="buyer",
        name="Sample Buyer Sp. z o.o.",
        country_code="PL",
        address_line_1="ul. Klienta 2",
        tax_id="5250001002",
    )
    service.add_body(
        uuid=handle.uuid,
        issue_date=date(2026, 3, 31),
        invoice_type="VAT",
    )
    service.add_line(
        uuid=handle.uuid,
        name="Consulting service",
        quantity=Decimal("1"),
        unit_price_net=Decimal("100.00"),
        sale_category="STANDARD",
        vat_rate="23",
    )

    return service, handle.uuid


def test_create_invoice_download_link_saves_xml_and_returns_absolute_url(
    tmp_path: Path,
) -> None:
    builder_service, builder_uuid = _create_ready_builder()
    download_service = InvoiceDownloadService(builder_service=builder_service)
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://downloads.example",
    )

    result = download_service.create_invoice_download_link(
        uuid=builder_uuid,
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


def test_download_invoice_route_serves_saved_invoice_xml(tmp_path: Path) -> None:
    builder_service, builder_uuid = _create_ready_builder()
    download_service = InvoiceDownloadService(builder_service=builder_service)
    settings = AppSettings(
        default_export_directory=tmp_path,
        resource_server_url="http://testserver",
    )
    result = download_service.create_invoice_download_link(
        uuid=builder_uuid,
        settings=settings,
    )

    app = create_server(settings).http_app(transport="streamable-http")

    with TestClient(app) as client:
        response = client.get(f"/downloads/invoices/{result.download_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "Consulting service" in response.text
