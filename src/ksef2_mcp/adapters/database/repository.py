import abc
import json
from collections.abc import Sequence
from uuid import UUID

from ksef2.domain.models import BatchSessionState
from ksef2.domain.models.session import OnlineSessionState
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from ksef2_mcp.adapters.database import orm
from ksef2_mcp.domain.enums import InvoiceStatus
from ksef2_mcp.domain.models import Invoice, SessionHandle, Submission
from ksef2_mcp.ports.repository import (
    AbstractSessionStateRepository,
    AbstractInvoiceRepository,
)


def _load_session_state(payload: str) -> OnlineSessionState | BatchSessionState:
    data = json.loads(payload)
    if "valid_until" in data:
        return OnlineSessionState.model_validate(data)
    return BatchSessionState.model_validate(data)


def _dump_session_state(
    state: OnlineSessionState | BatchSessionState | None,
) -> str | None:
    if state is None:
        return None
    return state.model_dump_json()


class AbstractSubmissionRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, submission: Submission) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, submission_id: str) -> Submission | None:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, submission: Submission) -> None:
        raise NotImplementedError


class SQLAlchemySessionStateRepository(AbstractSessionStateRepository):
    def __init__(self, session: Session):
        self._session = session

    def add_state(self, state: SessionHandle) -> None:
        self._session.execute(
            insert(orm.session_states).values(
                uuid=str(state.uuid),
                state_json=state.state.model_dump_json(),
                date_created=state.date_created,
                date_closed=state.date_closed,
            )
        )

    def get_state(self, uuid: UUID) -> SessionHandle | None:
        row = (
            self._session.execute(
                select(orm.session_states).where(orm.session_states.c.uuid == str(uuid))
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return SessionHandle(
            uuid=UUID(row["uuid"]),
            state=_load_session_state(row["state_json"]),
            date_created=row["date_created"],
            date_closed=row["date_closed"],
        )

    def get_state_or_raise(self, uuid: UUID) -> SessionHandle:
        state = self.get_state(uuid)
        if state is None:
            raise ValueError(f"No session state with UUID {uuid} found")
        return state

    def list_all(self) -> Sequence[SessionHandle]:
        rows = self._session.execute(
            select(orm.session_states).order_by(
                orm.session_states.c.date_created.desc()
            )
        ).mappings()
        return [
            SessionHandle(
                uuid=UUID(row["uuid"]),
                state=_load_session_state(row["state_json"]),
                date_created=row["date_created"],
                date_closed=row["date_closed"],
            )
            for row in rows
        ]


class SQLAlchemyInvoiceRepository(AbstractInvoiceRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, invoice: Invoice) -> None:
        self._session.execute(
            insert(orm.invoices).values(**invoice.model_dump(mode="python"))
        )

    def get(self, invoice_id: str) -> Invoice | None:
        row = (
            self._session.execute(
                select(orm.invoices).where(orm.invoices.c.invoice_id == invoice_id)
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        return Invoice.model_validate(dict(row))

    def list_all(self, status: InvoiceStatus | None = None) -> Sequence[Invoice]:
        statement = select(orm.invoices).order_by(orm.invoices.c.created_at.desc())
        if status is not None:
            statement = statement.where(orm.invoices.c.status == status.value)
        rows = self._session.execute(statement).mappings()
        return [Invoice.model_validate(dict(row)) for row in rows]

    def update(self, invoice: Invoice) -> None:
        payload = invoice.model_dump(mode="python")
        invoice_id = payload.pop("invoice_id")
        self._session.execute(
            update(orm.invoices)
            .where(orm.invoices.c.invoice_id == invoice_id)
            .values(**payload)
        )


class SQLAlchemySubmissionRepository(AbstractSubmissionRepository):
    def __init__(self, session: Session):
        self._session = session

    def add(self, submission: Submission) -> None:
        payload = submission.model_dump(mode="python")
        payload["session_state_json"] = _dump_session_state(
            submission.session_state_json
        )
        payload["details_json"] = (
            json.dumps(submission.details) if submission.details is not None else None
        )
        payload.pop("details")
        self._session.execute(insert(orm.submissions).values(**payload))

    def get(self, submission_id: str) -> Submission | None:
        row = (
            self._session.execute(
                select(orm.submissions).where(
                    orm.submissions.c.submission_id == submission_id
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        payload = dict(row)
        details_json = payload.pop("details_json")
        session_state_json = payload["session_state_json"]
        payload["details"] = (
            json.loads(details_json) if details_json is not None else None
        )
        payload["session_state_json"] = (
            OnlineSessionState.model_validate_json(session_state_json)
            if session_state_json is not None
            else None
        )
        return Submission.model_validate(payload)

    def update(self, submission: Submission) -> None:
        payload = submission.model_dump(mode="python")
        submission_id = payload.pop("submission_id")
        payload["session_state_json"] = _dump_session_state(
            submission.session_state_json
        )
        payload["details_json"] = (
            json.dumps(submission.details) if submission.details is not None else None
        )
        payload.pop("details")
        self._session.execute(
            update(orm.submissions)
            .where(orm.submissions.c.submission_id == submission_id)
            .values(**payload)
        )


class InMemorySessionStateRepository(AbstractSessionStateRepository):
    def __init__(self, states: dict[UUID, SessionHandle] | None = None):
        self._states = {} if states is None else states

    def add_state(self, state: SessionHandle) -> None:
        self._states[state.uuid] = state

    def get_state(self, uuid: UUID) -> SessionHandle | None:
        return self._states.get(uuid)

    def get_state_or_raise(self, uuid: UUID) -> SessionHandle:
        state = self.get_state(uuid)
        if state is None:
            raise ValueError(f"No session state with UUID {uuid} found")
        return state

    def list_all(self) -> Sequence[SessionHandle]:
        return list(self._states.values())
