import abc
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from typing import Literal, Self
from uuid import UUID

from ksef2.domain.models.fa3.body import InvoiceType, SaleCategory, VatRate
from ksef2.services import FA3InvoiceBuilder
from pydantic import ValidationError

from ksef2_mcp import errors
from ksef2_mcp.adapters.uow import fresh_uow
from ksef2_mcp.domain.models import InvoiceBuilderHandle, PendingInvoiceBody


class BaseInvoiceBuilder(abc.ABC):
    @abc.abstractmethod
    def create_invoice_builder(self) -> UUID:
        raise NotImplementedError

    @abc.abstractmethod
    def add_header(
        self,
        uuid: UUID,
        system_info: str,
        generation_timestamp: datetime | str | None = None,
    ) -> Self: ...


class LocalInvoiceBuilderService(BaseInvoiceBuilder):
    def __init__(self):
        pass

    def _normalize_wrapped_text(self, value: str) -> str:
        normalized = value.strip()
        while (
            len(normalized) >= 2
            and normalized[0] == normalized[-1]
            and normalized[0] in {"'", '"'}
        ):
            normalized = normalized[1:-1].strip()
        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_enum(
        self,
        enum_type: type[Enum],
        value: Enum | str,
        *,
        field_name: str,
        aliases: dict[str, Enum] | None = None,
    ) -> Enum:
        if isinstance(value, enum_type):
            return value

        normalized = self._normalize_wrapped_text(str(value))
        lookup = normalized.casefold()

        if aliases is not None and lookup in aliases:
            return aliases[lookup]

        for member in enum_type:
            if lookup in {member.name.casefold(), str(member.value).casefold()}:
                return member

        allowed_values = ", ".join(
            [member.name for member in enum_type]
            + [str(member.value) for member in enum_type]
        )
        raise errors.InvalidInputError(
            f"Invalid {field_name} {value!r}. Allowed values include: {allowed_values}"
        )

    def _normalize_sale_category(
        self, sale_category: SaleCategory | str
    ) -> SaleCategory:
        return self._normalize_enum(
            SaleCategory,
            sale_category,
            field_name="sale_category",
        )

    def _normalize_vat_rate(
        self,
        vat_rate: VatRate | str | None,
        *,
        sale_category: SaleCategory,
    ) -> VatRate | None:
        if vat_rate is None and sale_category is SaleCategory.STANDARD:
            return VatRate.VAT_23
        if vat_rate is None:
            return None
        return self._normalize_enum(
            VatRate,
            vat_rate,
            field_name="vat_rate",
        )

    def _normalize_invoice_type(
        self, invoice_type: InvoiceType | str
    ) -> InvoiceType:
        return self._normalize_enum(
            InvoiceType,
            invoice_type,
            field_name="invoice_type",
            aliases={
                "basic": InvoiceType.VAT,
                "standard": InvoiceType.VAT,
            },
        )

    def _apply_pending_body(self, builder_handle: InvoiceBuilderHandle) -> None:
        if builder_handle.pending_body is None:
            builder_handle.refresh_steps()
            return
        if "lines" in builder_handle.builder.missing_steps():
            builder_handle.refresh_steps()
            return

        builder_handle.builder.body(**builder_handle.pending_body.model_dump())
        builder_handle.pending_body = None
        builder_handle.refresh_steps()

    def create_invoice_builder(self) -> InvoiceBuilderHandle:
        try:
            with fresh_uow() as uow:
                invoice_builder = FA3InvoiceBuilder()
                builder_handle = InvoiceBuilderHandle(
                    builder=invoice_builder,
                )

                uow.invoice_builders.add_builder(builder_handle)
                builder_handle.refresh_steps()

                return builder_handle
        except Exception as exc:
            raise errors.SessionManagementError(
                f"Failed to create an invoice builder: {exc}"
            ) from exc

    def add_header(
        self,
        uuid: UUID,
        system_info: str,
        generation_timestamp: datetime | str | None = None,
    ):
        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)

                builder_handle.builder.header(
                    generation_timestamp=generation_timestamp, system_info=system_info
                )

                builder_handle.mark_step_completed("header")
                builder_handle.refresh_steps()

                return builder_handle

        except Exception as exc:
            raise errors.InvoiceBuilderError("Failed to add header to builder") from exc

    def add_entity(
        self,
        uuid: UUID,
        entity_type: Literal["seller", "buyer"],
        name: str,
        country_code: str,
        address_line_1: str,
        tax_id: str | None = None,
        address_line_2: str | None = None,
        gln: str | None = None,
        eu_vat_id: str | None = None,
        customer_number: str | None = None,
        email: str | None = None,
        phone: str | None = None,
    ) -> InvoiceBuilderHandle:
        normalized_tax_id = self._normalize_optional_text(tax_id)
        if entity_type == "seller" and normalized_tax_id is None:
            raise errors.InvalidInputError("seller tax_id is required")

        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)

                match entity_type:
                    case "seller":
                        builder_handle.builder.seller(
                            name=name,
                            country_code=country_code,
                            address_line_1=address_line_1,
                            tax_id=normalized_tax_id,
                            address_line_2=self._normalize_optional_text(address_line_2),
                            gln=self._normalize_optional_text(gln),
                            eu_vat_id=self._normalize_optional_text(eu_vat_id),
                            customer_number=self._normalize_optional_text(customer_number),
                            email=self._normalize_optional_text(email),
                            phone=self._normalize_optional_text(phone),
                        )
                    case "buyer":
                        builder_handle.builder.buyer(
                            name=name,
                            country_code=country_code,
                            address_line_1=address_line_1,
                            tax_id=normalized_tax_id,
                            address_line_2=self._normalize_optional_text(address_line_2),
                            gln=self._normalize_optional_text(gln),
                            eu_vat_id=self._normalize_optional_text(eu_vat_id),
                            customer_number=self._normalize_optional_text(customer_number),
                            email=self._normalize_optional_text(email),
                            phone=self._normalize_optional_text(phone),
                        )
                    case _:
                        raise ValueError(f"Invalid entity type: {entity_type}")

                builder_handle.mark_step_completed(entity_type)
                builder_handle.refresh_steps()

                return builder_handle

        except errors.KsefMcpError:
            raise
        except Exception as exc:
            raise errors.InvoiceBuilderError("Failed to add entity to builder") from exc

    def add_line(
        self,
        uuid: UUID,
        name: str,
        quantity: Decimal,
        unit_price_net: Decimal,
        vat_rate: VatRate | str | None = None,
        unit_of_measure: str = "szt",
        supply_date: date | None = None,
        discount_amount: Decimal | None = Decimal("0.00"),
        sale_category: SaleCategory | str = SaleCategory.STANDARD,
        net_amount: Decimal | None = None,
        vat_amount: Decimal | None = None,
        gross_amount: Decimal | None = None,
        unique_id: str | None = None,
        sku: str | None = None,
        gtin: str | None = None,
        pkwiu: str | None = None,
        cn: str | None = None,
        pkob: str | None = None,
        before_correction: bool = False,
    ) -> InvoiceBuilderHandle:
        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)
                normalized_sale_category = self._normalize_sale_category(sale_category)
                normalized_vat_rate = self._normalize_vat_rate(
                    vat_rate,
                    sale_category=normalized_sale_category,
                )

                builder_handle.builder.add_line(
                    name=name,
                    quantity=quantity,
                    unit_price_net=unit_price_net,
                    vat_rate=normalized_vat_rate,
                    unit_of_measure=unit_of_measure,
                    supply_date=supply_date,
                    discount_amount=discount_amount,
                    sale_category=normalized_sale_category,
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

                builder_handle.mark_step_completed("lines")
                self._apply_pending_body(builder_handle)

                return builder_handle
        except (ValidationError, ValueError) as exc:
            message = str(exc)
            if "STANDARD sale_category requires vat_rate equal to" in message:
                raise errors.InvalidInputError(
                    "Invalid VAT configuration for line item: "
                    "sale_category='STANDARD' only supports VAT rates 23, 22, 8, "
                    "7, or 5. Use a matching sale_category for values like "
                    "'zw', 'np', or 'oo'."
                ) from exc
            raise errors.InvalidInputError(
                f"Failed to add line to builder: {exc}"
            ) from exc
        except errors.KsefMcpError:
            raise
        except Exception as exc:
            raise errors.InvoiceBuilderError(
                f"Failed to add line to builder: {exc}"
            ) from exc

    def add_body(
        self,
        uuid: UUID,
        issue_date: date,
        currency: str = "PLN",
        issue_place: str | None = None,
        invoice_type: InvoiceType | str = InvoiceType.VAT,
        warehouse_documents: Sequence[str] | None = None,
        date_of_supply: date | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> InvoiceBuilderHandle:
        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)

                builder_handle.pending_body = PendingInvoiceBody(
                    issue_date=issue_date,
                    currency=currency,
                    issue_place=issue_place,
                    invoice_type=self._normalize_invoice_type(invoice_type),
                    warehouse_documents=tuple(warehouse_documents)
                    if warehouse_documents is not None
                    else None,
                    date_of_supply=date_of_supply,
                    period_start=period_start,
                    period_end=period_end,
                )

                self._apply_pending_body(builder_handle)

                return builder_handle

        except (ValidationError, ValueError) as exc:
            raise errors.InvalidInputError(
                f"Failed to add body to builder: {exc}"
            ) from exc
        except errors.KsefMcpError:
            raise
        except Exception as exc:
            raise errors.InvoiceBuilderError(
                f"Failed to add body to builder: {exc}"
            ) from exc

    def get_builder_handle(self, uuid: UUID) -> InvoiceBuilderHandle:
        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)
                builder_handle.refresh_steps()
                return builder_handle
        except Exception as exc:
            raise errors.InvoiceBuilderError(
                f"Failed to get invoice builder handle: {exc}"
            ) from exc

    def build_invoice(self, uuid: UUID) -> str:
        try:
            with fresh_uow() as uow:
                builder_handle = uow.invoice_builders.get_builder_or_raise(uuid)
                self._apply_pending_body(builder_handle)
                return builder_handle.builder.to_xml()
        except Exception as exc:
            raise errors.InvoiceBuilderError(f"Failed to build invoice: {exc}") from exc


@lru_cache(maxsize=1)
def get_builder_service() -> LocalInvoiceBuilderService:
    return LocalInvoiceBuilderService()
