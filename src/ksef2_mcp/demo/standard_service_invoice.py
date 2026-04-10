"""Runnable MVP demo for a realistic recurring B2B service invoice."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from ksef2_mcp.services.drafts import (
    CallOperation,
    DoneOperation,
    DraftRuntimeService,
    SpawnOperation,
)


def build_standard_service_invoice_xml() -> str:
    """Build a realistic FA(3) invoice through the draft/context runtime."""
    service = DraftRuntimeService()
    created = service.create_draft("standard_invoice")
    update = service.update_draft(
        created.draft_id,
        [
            CallOperation(
                context_id="root",
                method="header",
                args={"system_info": "ksef2-mcp demo / LinkedIn MVP"},
            ),
            CallOperation(
                context_id="root",
                method="seller",
                args={
                    "name": "BrightAnalytics Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Prosta 12, 00-850 Warszawa",
                    "tax_id": "5250001001",
                    "email": "faktury@brightanalytics.pl",
                    "phone": "+48221234567",
                },
            ),
            CallOperation(
                context_id="root",
                method="buyer",
                args={
                    "name": "Northwind Studio Sp. z o.o.",
                    "country_code": "PL",
                    "address_line_1": "ul. Strefowa 8, 61-731 Poznan",
                    "tax_id": "7830002002",
                    "customer_number": "NW-2026-014",
                    "email": "ap@northwindstudio.pl",
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
            CallOperation(
                context_id="body_1",
                method="invoice_number",
                args={"value": "FV/03/2026/BA/001"},
            ),
            CallOperation(
                context_id="body_1",
                method="issue_place",
                args={"value": "Warszawa"},
            ),
            CallOperation(
                context_id="body_1",
                method="billing_period",
                args={
                    "period_start": date(2026, 3, 1),
                    "period_end": date(2026, 3, 31),
                },
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
                    "name": "Monthly analytics and reporting subscription",
                    "quantity": Decimal("1"),
                    "unit_of_measure": "mies.",
                    "unit_price_net": Decimal("1800.00"),
                    "vat_rate": "23",
                },
            ),
            CallOperation(
                context_id="rows_1",
                method="add_line",
                args={
                    "name": "Dashboard customization workshop",
                    "quantity": Decimal("4"),
                    "unit_of_measure": "h",
                    "unit_price_net": Decimal("220.00"),
                    "discount_amount": Decimal("80.00"),
                    "vat_rate": "23",
                    "supply_date": date(2026, 3, 27),
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
    failures = [
        operation
        for operation in update.operations
        if operation.status != "succeeded"
    ]
    if failures:
        messages = ", ".join(
            failure.message or f"{failure.op}:{failure.method}"
            for failure in failures
        )
        raise RuntimeError(f"Failed to build demo invoice draft: {messages}")

    built = service.build_draft(created.draft_id, output_format="xml")
    service.delete_draft(created.draft_id)
    return built.content


def write_standard_service_invoice_xml(
    target_path: Path | None = None,
) -> Path:
    """Write the demo invoice XML to disk and return the created path."""
    output_path = target_path or Path("output") / "standard-service-invoice.xml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_standard_service_invoice_xml(), encoding="utf-8")
    return output_path


def main() -> int:
    output_path = write_standard_service_invoice_xml()
    print(f"Saved demo FA(3) invoice XML to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
