from datetime import date
from decimal import Decimal

import pytest

from ksef2_mcp.adapters.uow import _SHARED_IN_MEMORY_STORE
from ksef2_mcp.errors import InvalidInputError
from ksef2_mcp.services.builder import LocalInvoiceBuilderService


@pytest.fixture(autouse=True)
def clear_in_memory_builder_store() -> None:
    _SHARED_IN_MEMORY_STORE["sessions"].clear()
    _SHARED_IN_MEMORY_STORE["builders"].clear()


def test_create_invoice_builder_reports_real_missing_steps() -> None:
    service = LocalInvoiceBuilderService()

    handle = service.create_invoice_builder()

    assert handle.completed_steps == []
    assert handle.missing_steps == ("seller", "buyer", "body", "lines")
    assert handle.is_ready_to_build is False


def test_add_invoice_body_can_be_deferred_until_lines_exist() -> None:
    service = LocalInvoiceBuilderService()
    handle = service.create_invoice_builder()

    deferred = service.add_body(
        uuid=handle.uuid,
        issue_date=date(2026, 3, 31),
        invoice_type="VAT",
    )

    assert deferred.completed_steps == []
    assert deferred.missing_steps == ("seller", "buyer", "body", "lines")

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

    ready = service.add_line(
        uuid=handle.uuid,
        name="Consulting service",
        quantity=Decimal("1"),
        unit_price_net=Decimal("100.00"),
        sale_category="STANDARD",
        vat_rate=None,
    )

    assert ready.completed_steps == ["seller", "buyer", "body", "lines"]
    assert ready.missing_steps == ()
    assert ready.is_ready_to_build is True


def test_build_invoice_supports_normalized_aliases() -> None:
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
        invoice_type="basic",
    )
    service.add_line(
        uuid=handle.uuid,
        name="Consulting service",
        quantity=Decimal("1"),
        unit_price_net=Decimal("100.00"),
        sale_category="STANDARD",
        vat_rate="23",
    )

    xml = service.build_invoice(handle.uuid)

    assert "Sample Seller Sp. z o.o." in xml
    assert "Sample Buyer Sp. z o.o." in xml
    assert "Consulting service" in xml


def test_add_line_accepts_quoted_vat_rate_values() -> None:
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
        invoice_type="basic",
    )

    ready = service.add_line(
        uuid=handle.uuid,
        name="Consulting service",
        quantity=Decimal("1"),
        unit_price_net=Decimal("100.00"),
        sale_category="STANDARD",
        vat_rate='"23"',
    )

    assert ready.is_ready_to_build is True


def test_add_line_reports_clear_standard_vat_conflict() -> None:
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
        invoice_type="basic",
    )

    with pytest.raises(
        InvalidInputError,
        match="sale_category='STANDARD' only supports VAT rates 23, 22, 8, 7, or 5",
    ):
        service.add_line(
            uuid=handle.uuid,
            name="Consulting service",
            quantity=Decimal("1"),
            unit_price_net=Decimal("100.00"),
            sale_category="STANDARD",
            vat_rate="oo",
        )


def test_add_seller_requires_tax_id_with_clear_message() -> None:
    service = LocalInvoiceBuilderService()
    handle = service.create_invoice_builder()

    with pytest.raises(InvalidInputError, match="seller tax_id is required"):
        service.add_entity(
            uuid=handle.uuid,
            entity_type="seller",
            name="Sample Seller Sp. z o.o.",
            country_code="PL",
            address_line_1="ul. Prosta 1",
        )


def test_add_body_rejects_unknown_invoice_type_with_clear_message() -> None:
    service = LocalInvoiceBuilderService()
    handle = service.create_invoice_builder()

    with pytest.raises(InvalidInputError, match="Invalid invoice_type"):
        service.add_body(
            uuid=handle.uuid,
            issue_date=date(2026, 3, 31),
            invoice_type="not-a-real-type",
        )
