import asyncio
from uuid import uuid4

from ksef2_mcp.domain.outputs import InvoiceDownloadLinkResult
from ksef2_mcp.server import create_server
from ksef2_mcp.services.builder import LocalInvoiceBuilderService
from ksef2_mcp.tools import register_tools
from ksef2_mcp.tools.builder import add_invoice_entity, create_invoice_download_link


def test_add_invoice_entity_passes_tax_id_and_normalizes_blank_optionals(
    monkeypatch,
) -> None:
    seen = {}
    expected = LocalInvoiceBuilderService().create_invoice_builder()

    class StubService:
        def add_entity(self, **kwargs):
            seen.update(kwargs)
            return expected

    monkeypatch.setattr(
        "ksef2_mcp.tools.builder.get_builder_service",
        lambda: StubService(),
    )

    result = add_invoice_entity(
        uuid=uuid4(),
        entity_type="seller",
        name="ACME Sp. z o.o.",
        country_code="PL",
        address_line_1="ul. Prosta 1",
        tax_id="5250001009",
        address_line_2="",
        gln="",
        eu_vat_id="",
        customer_number="",
        email="",
        phone="",
    )

    assert result.uuid == expected.uuid
    assert seen["tax_id"] == "5250001009"
    assert seen["address_line_2"] is None
    assert seen["gln"] is None
    assert seen["eu_vat_id"] is None
    assert seen["customer_number"] is None
    assert seen["email"] is None
    assert seen["phone"] is None


def test_add_invoice_entity_tool_exposes_tax_id_as_string_schema() -> None:
    async def list_tools():
        mcp = create_server()
        register_tools(mcp)
        return await mcp.list_tools()

    tools = asyncio.run(list_tools())
    add_invoice_entity_tool = next(
        tool for tool in tools if tool.name == "add_invoice_entity"
    )
    tax_id_schema = add_invoice_entity_tool.parameters["properties"]["tax_id"]

    assert tax_id_schema["type"] == "string"
    assert "anyOf" not in tax_id_schema
    assert "Required for seller" in tax_id_schema["description"]


def test_create_invoice_download_link_tool_delegates_to_service(
    monkeypatch,
) -> None:
    expected = InvoiceDownloadLinkResult(
        download_id="download-1",
        download_url="http://testserver/downloads/invoices/download-1",
        file_name="invoice.xml",
        file_path="/tmp/invoice.xml",
        media_type="application/xml",
    )
    seen = {}

    class StubService:
        def create_invoice_download_link(self, **kwargs):
            seen.update(kwargs)
            return expected

    monkeypatch.setattr(
        "ksef2_mcp.tools.builder.get_invoice_download_service",
        lambda: StubService(),
    )

    result = create_invoice_download_link(
        uuid=uuid4(),
        file_format="pdf",
        file_name="invoice.xml",
    )

    assert result == expected
    assert seen["file_format"] == "pdf"
    assert seen["file_name"] == "invoice.xml"
