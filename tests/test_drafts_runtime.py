from datetime import date
from decimal import Decimal

import pytest

from ksef2_mcp.adapters.draft_store import _SHARED_DRAFT_STATES
from ksef2_mcp.errors import ResourceNotFoundError
from ksef2_mcp.services.drafts import (
    CallOperation,
    DoneOperation,
    SpawnOperation,
    get_draft_runtime_service,
)


@pytest.fixture(autouse=True)
def clear_draft_runtime() -> None:
    _SHARED_DRAFT_STATES.clear()


def _get_method_schema(methods_result, method_name: str) -> dict:
    return next(
        method.payload_schema
        for method in methods_result.methods
        if method.name == method_name
    )


def _spawn(
    context_id: str,
    method: str,
    new_context_id: str,
    *,
    op_id: str | None = None,
    args: dict | None = None,
) -> SpawnOperation:
    return SpawnOperation(
        op_id=op_id,
        context_id=context_id,
        method=method,
        new_context_id=new_context_id,
        args=args,
    )


def _call(
    context_id: str,
    method: str,
    *,
    op_id: str | None = None,
    args: dict | None = None,
) -> CallOperation:
    return CallOperation(
        op_id=op_id,
        context_id=context_id,
        method=method,
        args=args,
    )


def _done(
    context_id: str,
    method: str = "done",
    *,
    op_id: str | None = None,
) -> DoneOperation:
    return DoneOperation(
        op_id=op_id,
        context_id=context_id,
        method=method,
    )


def test_create_draft_registers_root_context() -> None:
    service = get_draft_runtime_service()

    created = service.create_draft("standard_invoice")
    contexts = service.get_contexts(created.draft_id)

    assert created.draft_type == "standard_invoice"
    assert created.root_context_id == "root"
    assert [context.context_id for context in contexts.contexts] == ["root"]


def test_get_possible_methods_is_context_specific() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    root_methods = service.get_possible_methods(created.draft_id, "root")
    root_method_names = {method.name for method in root_methods.methods}

    assert "standard" in root_method_names
    assert "header" in root_method_names
    assert "add_line" not in root_method_names

    update = service.update_draft(
        created.draft_id,
        [
            _spawn("root", "standard", "body_1")
        ],
    )

    assert update.operations[0].status == "succeeded"

    body_methods = service.get_possible_methods(created.draft_id, "body_1")
    body_method_names = {method.name for method in body_methods.methods}

    assert "rows" in body_method_names
    assert "issue_date" in body_method_names
    assert "seller" not in body_method_names


def test_get_possible_methods_excludes_internal_and_model_methods() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    root_methods = service.get_possible_methods(created.draft_id, "root")
    root_method_names = {method.name for method in root_methods.methods}

    assert "build" not in root_method_names
    assert "to_xml" not in root_method_names
    assert "from_model" not in root_method_names
    assert not any(name.endswith("_model") for name in root_method_names)


def test_get_possible_methods_classifies_spawn_call_and_done_methods() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    root_methods = service.get_possible_methods(created.draft_id, "root")
    root_method_map = {method.name: method for method in root_methods.methods}

    assert root_method_map["standard"].operation_type == "spawn"
    assert root_method_map["seller"].operation_type == "call"

    update = service.update_draft(
        created.draft_id,
        [_spawn("root", "standard", "body_1")],
    )
    assert update.operations[0].status == "succeeded"

    body_methods = service.get_possible_methods(created.draft_id, "body_1")
    body_method_map = {method.name: method for method in body_methods.methods}

    assert body_method_map["done"].operation_type == "done"
    assert body_method_map["issue_date"].operation_type == "call"


def test_get_possible_methods_exposes_builder_metadata_for_common_root_fields() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    root_methods = service.get_possible_methods(created.draft_id, "root")
    seller_schema = _get_method_schema(root_methods, "seller")
    country_code_schema = seller_schema["properties"]["country_code"]

    assert seller_schema["type"] == "object"
    assert seller_schema["additionalProperties"] is False
    assert country_code_schema["type"] == "string"
    assert country_code_schema["format"] == "country-code"
    assert country_code_schema["minLength"] == 2
    assert country_code_schema["maxLength"] == 2
    assert country_code_schema["description"]
    assert country_code_schema["examples"] == ["PL", "DE"]
    assert country_code_schema["x-builder-format"] == "country-code"
    assert country_code_schema["x-builder-prefer-omit-when-null"] is True


def test_get_possible_methods_normalizes_add_line_payload_for_llm_use() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    update = service.update_draft(
        created.draft_id,
        [
            _spawn("root", "standard", "body_1"),
            _spawn("body_1", "rows", "rows_1"),
        ],
    )

    assert all(operation.status == "succeeded" for operation in update.operations)

    rows_methods = service.get_possible_methods(created.draft_id, "rows_1")
    add_line_schema = _get_method_schema(rows_methods, "add_line")
    properties = add_line_schema["properties"]

    assert add_line_schema["type"] == "object"
    assert add_line_schema["additionalProperties"] is False
    assert add_line_schema["required"] == ["name", "quantity", "unit_price_net"]

    quantity_schema = properties["quantity"]
    assert quantity_schema["type"] == "string"
    assert quantity_schema["format"] == "decimal"
    assert quantity_schema["examples"] == ["1", "2.5"]
    assert quantity_schema["x-builder-format"] == "decimal-string"

    vat_rate_schema = properties["vat_rate"]
    assert vat_rate_schema["type"] == "string"
    assert "23" in vat_rate_schema["enum"]
    assert "zw" in vat_rate_schema["enum"]
    assert vat_rate_schema["x-builder-format"] == "enum-string"

    vat_classification_schema = properties["vat_classification"]
    assert vat_classification_schema["$ref"] == "#/$defs/VatClassification"
    assert (
        vat_classification_schema["x-builder-schema-ref"]
        == "ksef2.domain.models.fa3.body.tax.VatClassification"
    )
    assert vat_classification_schema["x-builder-priority"] == "advanced"

    net_amount_schema = properties["net_amount"]
    assert net_amount_schema["type"] == "string"
    assert net_amount_schema["format"] == "decimal"
    assert net_amount_schema["x-builder-priority"] == "override"

    supply_date_schema = properties["supply_date"]
    assert supply_date_schema["type"] == "string"
    assert supply_date_schema["format"] == "date"
    assert supply_date_schema["x-builder-format"] == "date"


def test_update_draft_can_drive_nested_builder_and_build_xml() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    update = service.update_draft(
        created.draft_id,
        [
            _call("root", "header", args={"system_info": "ksef2-mcp runtime"}),
            _call(
                "root",
                "seller",
                args={
                    "name": "Sample Seller Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 1",
                    "tax_id": "5250001001",
                },
            ),
            _call(
                "root",
                "buyer",
                args={
                    "name": "Sample Buyer Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Klienta 2",
                    "tax_id": "5250001002",
                },
            ),
            _spawn("root", "standard", "body_1"),
            _call("body_1", "issue_date", args={"value": date(2026, 3, 31)}),
            _call("body_1", "invoice_number", args={"value": "FV/03/2026/001"}),
            _spawn("body_1", "rows", "rows_1"),
            _call(
                "rows_1",
                "add_line",
                args={
                    "name": "Consulting service",
                    "quantity": Decimal("1"),
                    "unit_price_net": Decimal("100.00"),
                    "vat_rate": "23",
                },
            ),
            _done("rows_1"),
            _done("body_1"),
        ],
    )

    assert all(operation.status == "succeeded" for operation in update.operations)

    built = service.build_draft(created.draft_id, output_format="xml")

    assert built.output_format == "xml"
    assert "Sample Seller Sp. z o.o." in built.content
    assert "Consulting service" in built.content
    assert "FV/03/2026/001" in built.content


def test_update_draft_accepts_json_friendly_string_payloads() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    update = service.update_draft(
        created.draft_id,
        [
            _call("root", "header", args={"system_info": "ksef2-mcp runtime"}),
            _call(
                "root",
                "seller",
                args={
                    "name": "Sample Seller Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 1",
                    "tax_id": "5250001001",
                },
            ),
            _call(
                "root",
                "buyer",
                args={
                    "name": "Sample Buyer Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Klienta 2",
                    "tax_id": "5250001002",
                },
            ),
            _spawn("root", "standard", "body_1"),
            _call("body_1", "issue_date", args={"value": "2026-03-31"}),
            _call("body_1", "invoice_number", args={"value": "FV/03/2026/002"}),
            _spawn("body_1", "rows", "rows_1"),
            _call(
                "rows_1",
                "add_line",
                args={
                    "name": "Consulting service",
                    "quantity": "1",
                    "unit_price_net": "100.00",
                    "vat_rate": "23",
                },
            ),
            _done("rows_1"),
            _done("body_1"),
        ],
    )

    assert all(operation.status == "succeeded" for operation in update.operations)

    built = service.build_draft(created.draft_id, output_format="xml")

    assert "FV/03/2026/002" in built.content
    assert "Consulting service" in built.content


def test_update_draft_rejects_unexpected_payload_fields() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    update = service.update_draft(
        created.draft_id,
        [
            _call(
                "root",
                "seller",
                args={
                    "name": "Sample Seller Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 1",
                    "tax_id": "5250001001",
                    "surprise": "boom",
                },
            ),
        ],
    )

    assert len(update.operations) == 1
    assert update.operations[0].status == "failed"
    assert update.operations[0].error_code == "INVALID_INPUT"
    assert "surprise" in (update.operations[0].message or "")


def test_update_draft_preserves_typed_nested_model_arguments() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    update = service.update_draft(
        created.draft_id,
        [
            _call("root", "header", args={"system_info": "ksef2-mcp runtime"}),
            _call(
                "root",
                "seller",
                args={
                    "name": "Sample Seller Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 1",
                    "tax_id": "5250001001",
                },
            ),
            _call(
                "root",
                "buyer",
                args={
                    "name": "Sample Buyer Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Klienta 2",
                    "tax_id": "5250001002",
                },
            ),
            _spawn("root", "standard", "body_1"),
            _call("body_1", "issue_date", args={"value": "2026-03-31"}),
            _call("body_1", "invoice_number", args={"value": "FV/03/2026/003"}),
            _spawn("body_1", "rows", "rows_1"),
            _call(
                "rows_1",
                "add_line",
                args={
                    "name": "Line 1",
                    "quantity": "1",
                    "unit_price_net": "1626.01",
                    "vat_rate": "23",
                },
            ),
            _call(
                "rows_1",
                "add_line",
                args={
                    "name": "Line 2",
                    "quantity": "1",
                    "unit_price_net": "40.65",
                    "vat_rate": "23",
                },
            ),
            _call(
                "rows_1",
                "add_line",
                args={
                    "name": "Line 3",
                    "quantity": "1",
                    "unit_price_net": "0.95",
                    "vat_rate": "5",
                },
            ),
            _done("rows_1"),
            _call(
                "body_1",
                "summary_overrides",
                args={"value": {"total_gross": "2051.00"}},
            ),
            _done("body_1"),
        ],
    )

    assert all(operation.status == "succeeded" for operation in update.operations)

    built = service.build_draft(created.draft_id, output_format="model")

    assert built.content["body"]["summary_overrides"]["total_gross"] == "2051.00"


def test_delete_draft_removes_state() -> None:
    service = get_draft_runtime_service()
    created = service.create_draft("standard_invoice")

    deleted = service.delete_draft(created.draft_id)

    assert deleted.deleted is True
    with pytest.raises(ResourceNotFoundError):
        service.get_contexts(created.draft_id)
