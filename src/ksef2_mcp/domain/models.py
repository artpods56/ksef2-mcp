from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ksef2.domain.models import BatchSessionState
from ksef2.domain.models.session import OnlineSessionState
from pydantic import BaseModel, Field

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
