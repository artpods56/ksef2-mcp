from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastmcp.tools.function_tool import tool
from ksef2.domain.models.fa3.body import InvoiceType, SaleCategory, VatRate
from pydantic import Field

from ksef2_mcp.domain.models import InvoiceBuilderHandle
from ksef2_mcp.domain.outputs import (
    InvoiceBuilderHandleResult,
    InvoiceDownloadLinkResult,
)
from ksef2_mcp.services.builder import get_builder_service
from ksef2_mcp.services.invoice_downloads import get_invoice_download_service

BuilderUUID = Annotated[
    UUID,
    Field(
        description="UUID of an existing invoice builder handle.",
        examples=["2f1c3dbe-6e5a-4f8b-a9b7-d2d5f1b2a123"],
    ),
]

SystemInfo = Annotated[
    str,
    Field(
        description="Name/version of the system generating the invoice header.",
        examples=["ksef2-mcp/0.1.0"],
        min_length=1,
    ),
]

GenerationTimestamp = Annotated[
    datetime | str | None,
    Field(
        description=(
            "Optional header generation timestamp. Prefer ISO 8601 format when "
            "passed as a string, for example '2026-03-30T12:00:00'. If omitted, "
            "the underlying builder may use its default."
        ),
        examples=["2026-03-30T12:00:00", None],
    ),
]

EntityType = Annotated[
    Literal["seller", "buyer"],
    Field(
        description="Which invoice party to add or update.",
        examples=["seller", "buyer"],
    ),
]

EntityName = Annotated[
    str,
    Field(
        description="Legal or business name of the entity.",
        min_length=1,
        examples=["ACME Sp. z o.o."],
    ),
]

CountryCode = Annotated[
    str,
    Field(
        description="Two-letter ISO country code of the entity address.",
        min_length=2,
        max_length=2,
        examples=["PL", "DE"],
    ),
]

AddressLine1 = Annotated[
    str,
    Field(
        description="Primary address line, usually street and building number.",
        min_length=1,
        examples=["ul. Prosta 1"],
    ),
]

AddressLine2 = Annotated[
    str,
    Field(
        description=(
            "Optional secondary address line, such as apartment, suite, or district. "
            "Omit it or pass an empty string when unknown."
        ),
        examples=["lok. 12", ""],
        default="",
    ),
]

TaxId = Annotated[
    str,
    Field(
        description=(
            "Tax identification number for the entity. Required for seller, "
            "optional for buyer. Omit it or pass an empty string only when it "
            "does not apply to the buyer."
        ),
        examples=["5250001009", ""],
        default="",
    ),
]

GLN = Annotated[
    str,
    Field(
        description=(
            "Optional Global Location Number of the entity. Omit it or pass an "
            "empty string when unknown."
        ),
        examples=["5901234123457", ""],
        default="",
    ),
]

EUVatId = Annotated[
    str,
    Field(
        description=(
            "Optional EU VAT ID of the entity. Omit it or pass an empty string "
            "when unknown."
        ),
        examples=["PL5250001009", ""],
        default="",
    ),
]

CustomerNumber = Annotated[
    str,
    Field(
        description=(
            "Optional internal customer number. Omit it or pass an empty string "
            "when unknown."
        ),
        examples=["CUST-1001", ""],
        default="",
    ),
]

Email = Annotated[
    str,
    Field(
        description=(
            "Optional email address for the entity. Omit it or pass an empty "
            "string when unknown."
        ),
        examples=["billing@example.com", ""],
        default="",
    ),
]

Phone = Annotated[
    str,
    Field(
        description=(
            "Optional phone number for the entity. Omit it or pass an empty "
            "string when unknown."
        ),
        examples=["+48500100200", ""],
        default="",
    ),
]

LineName = Annotated[
    str,
    Field(
        description="Invoice line item name or description.",
        min_length=1,
        examples=["Consulting services"],
    ),
]

Quantity = Annotated[
    Decimal,
    Field(
        description="Quantity of goods or services.",
        examples=["1.00", "2.5"],
    ),
]

UnitPriceNet = Annotated[
    Decimal,
    Field(
        description="Net unit price of the line item.",
        examples=["100.00", "2499.99"],
    ),
]

VatRateValue = Annotated[
    VatRate | str | None,
    Field(
        description=(
            "Optional VAT rate. Accepts enum names or values such as 'VAT_23', "
            "'23', 'zw', or 'oo'. If omitted for the default STANDARD sale "
            "category, the builder uses 23%."
        ),
        examples=["23", "ZW", None],
        default=VatRate.VAT_23,
    ),
]

UnitOfMeasure = Annotated[
    str,
    Field(
        description="Unit of measure for the line item.",
        examples=["szt", "h", "kg"],
        default="szt",
    ),
]

SupplyDate = Annotated[
    date | None,
    Field(
        description="Optional supply date for the line item.",
        examples=["2026-03-30", None],
        default=None,
    ),
]

DiscountAmount = Annotated[
    Decimal | None,
    Field(
        description="Optional discount amount applied to the line item.",
        examples=["0.00", "10.50", None],
        default=Decimal("0.00"),
    ),
]

SaleCategoryValue = Annotated[
    SaleCategory | str,
    Field(
        description=(
            "Sale category for the line item. Accepts enum names or values, for "
            "example 'STANDARD', 'standard', 'exempt', or 'reverse_charge'."
        ),
        default=SaleCategory.STANDARD,
    ),
]

NetAmount = Annotated[
    Decimal | None,
    Field(
        description=(
            "Optional explicit net amount for the line item. Usually omitted and "
            "derived automatically."
        ),
        examples=["100.00", None],
        default=None,
    ),
]

VatAmount = Annotated[
    Decimal | None,
    Field(
        description=(
            "Optional explicit VAT amount for the line item. Usually omitted and "
            "derived automatically."
        ),
        examples=["23.00", None],
        default=None,
    ),
]

GrossAmount = Annotated[
    Decimal | None,
    Field(
        description=(
            "Optional explicit gross amount for the line item. Usually omitted "
            "and derived automatically."
        ),
        examples=["123.00", None],
        default=None,
    ),
]

UniqueId = Annotated[
    str | None,
    Field(
        description="Optional unique identifier for the line item.",
        examples=["line-001", None],
        default=None,
    ),
]

SKU = Annotated[
    str | None,
    Field(
        description="Optional stock keeping unit for the line item.",
        examples=["SKU-001", None],
        default=None,
    ),
]

GTIN = Annotated[
    str | None,
    Field(
        description="Optional GTIN for the line item.",
        examples=["05901234123457", None],
        default=None,
    ),
]

PKWIU = Annotated[
    str | None,
    Field(
        description="Optional PKWiU code for the line item.",
        examples=["62.02.30.0", None],
        default=None,
    ),
]

CN = Annotated[
    str | None,
    Field(
        description="Optional CN code for the line item.",
        examples=["84713000", None],
        default=None,
    ),
]

PKOB = Annotated[
    str | None,
    Field(
        description="Optional PKOB code for the line item.",
        examples=["1122", None],
        default=None,
    ),
]

BeforeCorrection = Annotated[
    bool,
    Field(
        description="Whether the line item refers to values before correction.",
        default=False,
    ),
]

IssueDate = Annotated[
    date,
    Field(
        description="Invoice issue date in ISO format YYYY-MM-DD.",
        examples=["2026-03-30"],
    ),
]

Currency = Annotated[
    str,
    Field(
        description="Invoice currency code.",
        examples=["PLN", "EUR"],
        default="PLN",
        min_length=3,
        max_length=3,
    ),
]

IssuePlace = Annotated[
    str | None,
    Field(
        description="Optional place where the invoice was issued.",
        examples=["Warsaw", None],
        default=None,
    ),
]

InvoiceTypeValue = Annotated[
    InvoiceType | str,
    Field(
        description=(
            "Invoice type. Accepts enum names such as 'VAT' or the full invoice "
            "type label. Common aliases like 'basic' are normalized to the "
            "basic VAT invoice type."
        ),
        default=InvoiceType.VAT,
    ),
]

WarehouseDocuments = Annotated[
    list[str] | None,
    Field(
        description="Optional list of related warehouse document identifiers.",
        examples=[["WZ/1/2026", "WZ/2/2026"], None],
        default=None,
    ),
]

DateOfSupply = Annotated[
    date | None,
    Field(
        description="Optional date of supply in ISO format YYYY-MM-DD.",
        examples=["2026-03-30", None],
        default=None,
    ),
]

PeriodStart = Annotated[
    date | None,
    Field(
        description="Optional billing period start date in ISO format YYYY-MM-DD.",
        examples=["2026-03-01", None],
        default=None,
    ),
]

PeriodEnd = Annotated[
    date | None,
    Field(
        description="Optional billing period end date in ISO format YYYY-MM-DD.",
        examples=["2026-03-31", None],
        default=None,
    ),
]

DownloadFileName = Annotated[
    str | None,
    Field(
        description=(
            "Optional download file name for the generated XML. "
            "If omitted, a default invoice-<builder-uuid>.xml name is used."
        ),
        examples=["invoice-2026-03-31.xml", None],
        default=None,
    ),
]

DownloadFileFormat = Annotated[
    Literal["xml", "pdf"],
    Field(
        description=(
            "Download format for the generated invoice artifact. Use 'xml' for "
            "the raw FA(3) invoice file or 'pdf' for a rendered PDF preview."
        ),
        examples=["xml", "pdf"],
        default="xml",
    ),
]


def _to_builder_result(
    handle: InvoiceBuilderHandle,
) -> InvoiceBuilderHandleResult:
    return InvoiceBuilderHandleResult(
        uuid=handle.uuid,
        completed_steps=list(handle.completed_steps),
        missing_steps=list(handle.missing_steps),
        is_ready_to_build=handle.is_ready_to_build,
    )


def _empty_string_to_none(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


@tool(
    name="create_invoice_builder",
    description=(
        "Create a new invoice builder handle. "
        "Use the returned UUID in subsequent builder tool calls."
    ),
)
def create_invoice_builder() -> InvoiceBuilderHandleResult:
    return _to_builder_result(get_builder_service().create_invoice_builder())


@tool(
    name="get_invoice_builder_handle",
    description=(
        "Get the current state of an invoice builder handle, including which "
        "steps are completed."
    ),
)
def get_invoice_builder_handle(
    uuid: BuilderUUID,
) -> InvoiceBuilderHandleResult:
    return _to_builder_result(get_builder_service().get_builder_handle(uuid))


@tool(
    name="add_invoice_header",
    description=("Add or update invoice header metadata for an existing builder."),
)
def add_invoice_header(
    uuid: BuilderUUID,
    system_info: SystemInfo,
    generation_timestamp: GenerationTimestamp = None,
) -> InvoiceBuilderHandleResult:
    return _to_builder_result(
        get_builder_service().add_header(
            uuid=uuid,
            system_info=system_info,
            generation_timestamp=generation_timestamp,
        )
    )


@tool(
    name="add_invoice_entity",
    description=(
        "Add or update a seller or buyer entity for an existing invoice builder."
    ),
)
def add_invoice_entity(
    uuid: BuilderUUID,
    entity_type: EntityType,
    name: EntityName,
    country_code: CountryCode,
    address_line_1: AddressLine1,
    tax_id: TaxId = "",
    address_line_2: AddressLine2 = "",
    gln: GLN = "",
    eu_vat_id: EUVatId = "",
    customer_number: CustomerNumber = "",
    email: Email = "",
    phone: Phone = "",
) -> InvoiceBuilderHandleResult:
    return _to_builder_result(
        get_builder_service().add_entity(
            uuid=uuid,
            entity_type=entity_type,
            name=name,
            country_code=country_code,
            address_line_1=address_line_1,
            tax_id=_empty_string_to_none(tax_id),
            address_line_2=_empty_string_to_none(address_line_2),
            gln=_empty_string_to_none(gln),
            eu_vat_id=_empty_string_to_none(eu_vat_id),
            customer_number=_empty_string_to_none(customer_number),
            email=_empty_string_to_none(email),
            phone=_empty_string_to_none(phone),
        )
    )


@tool(
    name="add_invoice_line",
    description=("Add a line item to an existing invoice builder."),
)
def add_invoice_line(
    uuid: BuilderUUID,
    name: LineName,
    quantity: Quantity,
    unit_price_net: UnitPriceNet,
    vat_rate: VatRateValue = VatRate.VAT_23,
    unit_of_measure: UnitOfMeasure = "szt",
    supply_date: SupplyDate = None,
    discount_amount: DiscountAmount = Decimal("0.00"),
    sale_category: SaleCategoryValue = SaleCategory.STANDARD,
    net_amount: NetAmount = None,
    vat_amount: VatAmount = None,
    gross_amount: GrossAmount = None,
    unique_id: UniqueId = None,
    sku: SKU = None,
    gtin: GTIN = None,
    pkwiu: PKWIU = None,
    cn: CN = None,
    pkob: PKOB = None,
    before_correction: BeforeCorrection = False,
) -> InvoiceBuilderHandleResult:
    return _to_builder_result(
        get_builder_service().add_line(
            uuid=uuid,
            name=name,
            quantity=quantity,
            unit_price_net=unit_price_net,
            vat_rate=vat_rate,
            unit_of_measure=unit_of_measure,
            supply_date=supply_date,
            discount_amount=discount_amount,
            sale_category=sale_category,
            net_amount=net_amount,
            vat_amount=vat_amount,
            gross_amount=gross_amount,
            unique_id=unique_id,
            sku=sku,
            gtin=gtin,
            pkwiu=pkwiu,
            cn=cn,
            pkob=pkob,
            before_correction=before_correction,
        )
    )


@tool(
    name="add_invoice_body",
    description=(
        "Add or update invoice body metadata for an existing builder. "
        "This can be called before any lines exist; the metadata is stored and "
        "applied automatically once the builder has at least one line."
    ),
)
def add_invoice_body(
    uuid: BuilderUUID,
    issue_date: IssueDate,
    currency: Currency = "PLN",
    issue_place: IssuePlace = None,
    invoice_type: InvoiceTypeValue = InvoiceType.VAT,
    warehouse_documents: WarehouseDocuments = None,
    date_of_supply: DateOfSupply = None,
    period_start: PeriodStart = None,
    period_end: PeriodEnd = None,
) -> InvoiceBuilderHandleResult:
    return _to_builder_result(
        get_builder_service().add_body(
            uuid=uuid,
            issue_date=issue_date,
            currency=currency,
            issue_place=issue_place,
            invoice_type=invoice_type,
            warehouse_documents=warehouse_documents,
            date_of_supply=date_of_supply,
            period_start=period_start,
            period_end=period_end,
        )
    )


@tool(
    name="build_invoice_xml",
    description=(
        "Build the final invoice XML from an existing builder and return it as "
        "a string."
    ),
)
def build_invoice_xml(
    uuid: BuilderUUID,
) -> str:
    return get_builder_service().build_invoice(uuid)


@tool(
    name="create_invoice_download_link",
    description=(
        "Build the final invoice XML from an existing builder, save it on the "
        "MCP server, and return a downloadable HTTP link."
    ),
)
def create_invoice_download_link(
    uuid: BuilderUUID,
    file_format: DownloadFileFormat = "xml",
    file_name: DownloadFileName = None,
) -> InvoiceDownloadLinkResult:
    return get_invoice_download_service().create_invoice_download_link(
        uuid=uuid,
        file_format=file_format,
        file_name=file_name,
    )
