from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from ksef2.domain.models import BatchSessionState
from ksef2.domain.models.fa3.body import InvoiceType
from ksef2.domain.models.session import OnlineSessionState
from pydantic import BaseModel, Field, ConfigDict

from ksef2.services import FA3InvoiceBuilder
from ksef2_mcp.domain.enums import InvoiceStatus, SubmissionStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SessionHandle(BaseModel):
    uuid: UUID = Field(
        description="Session handle identificator used for storage",
        default_factory=uuid4,
    )
    state: OnlineSessionState | BatchSessionState = Field(exclude=True)
    date_created: datetime = Field(
        description="Date when the session handle was created.",
        default_factory=_utcnow,
    )
    date_closed: datetime | None = None

    @property
    def reference_number(self) -> str:
        return self.state.reference_number

    @property
    def form_code(self):
        return self.state.form_code

    @property
    def is_open(self) -> bool:
        return self.date_closed is None

    def close(self):
        self.date_closed = datetime.now(UTC)


# [TODO delete this]
class Invoice(BaseModel):
    invoice_id: str
    status: InvoiceStatus
    invoice_xml: str
    created_at: datetime
    updated_at: datetime
    latest_submission_id: str | None = None


# [TODO delete this too]
class Submission(BaseModel):
    submission_id: str
    invoice_id: str
    invoice_reference_number: str
    status: SubmissionStatus
    created_at: datetime
    updated_at: datetime
    session_state_json: OnlineSessionState | None = None
    finalized_at: datetime | None = None
    ksef_number: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None


type InvoiceBuilderStep = Literal["header", "seller", "buyer", "body", "lines"]
_REQUIRED_INVOICE_BUILDER_STEPS = ("seller", "buyer", "body", "lines")


class PendingInvoiceBody(BaseModel):
    issue_date: date
    currency: str = "PLN"
    issue_place: str | None = None
    invoice_type: InvoiceType = InvoiceType.VAT
    warehouse_documents: tuple[str, ...] | None = None
    date_of_supply: date | None = None
    period_start: date | None = None
    period_end: date | None = None


class InvoiceBuilderHandle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uuid: UUID = Field(
        default_factory=uuid4,
        description="Invoice builder handle used for storage",
    )
    builder: FA3InvoiceBuilder = Field(
        description="FA(3) invoice builder instance",
    )
    completed_steps: list[InvoiceBuilderStep] = Field(
        default_factory=list,
        description="Completed steps for the invoice builder",
    )
    pending_body: PendingInvoiceBody | None = Field(
        default=None,
        exclude=True,
        description="Deferred body metadata applied once the builder has lines.",
    )

    @property
    def missing_steps(self) -> tuple[InvoiceBuilderStep, ...]:
        builder_missing = set(self.builder.missing_steps())
        return tuple(
            step for step in _REQUIRED_INVOICE_BUILDER_STEPS if step in builder_missing
        )

    @property
    def is_ready_to_build(self) -> bool:
        return not self.missing_steps

    def refresh_steps(self) -> None:
        header_completed = "header" in self.completed_steps
        builder_missing = set(self.builder.missing_steps())
        completed_steps: list[InvoiceBuilderStep] = []

        if header_completed:
            completed_steps.append("header")

        for step in _REQUIRED_INVOICE_BUILDER_STEPS:
            if step not in builder_missing:
                completed_steps.append(step)

        self.completed_steps = completed_steps
        if "body" not in builder_missing:
            self.pending_body = None

    def mark_step_completed(self, step: InvoiceBuilderStep) -> None:
        if step == "header" and step not in self.completed_steps:
            self.completed_steps.append(step)
            return

        self.refresh_steps()
