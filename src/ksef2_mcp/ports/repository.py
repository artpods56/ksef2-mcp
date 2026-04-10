import abc
from types import TracebackType
from typing import Self, Sequence
from uuid import UUID

from ksef2_mcp.domain import Invoice, InvoiceStatus, SessionHandle
from ksef2_mcp.domain.drafts import DraftSession


class AbstractSessionStateRepository(abc.ABC):
    @abc.abstractmethod
    def add_state(self, state: SessionHandle) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_state(self, uuid: UUID) -> SessionHandle | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_state_or_raise(self, uuid: UUID) -> SessionHandle:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[SessionHandle]:
        raise NotImplementedError


class AbstractDraftSessionRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, draft_session: DraftSession) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, draft_id: UUID) -> DraftSession | None:
        raise NotImplementedError

    @abc.abstractmethod
    def get_or_raise(self, draft_id: UUID) -> DraftSession:
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, draft_id: UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self) -> Sequence[DraftSession]:
        raise NotImplementedError


class AbstractInvoiceRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, invoice: Invoice) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, invoice_id: str) -> Invoice | None:
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self, status: InvoiceStatus | None = None) -> Sequence[Invoice]:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, invoice: Invoice) -> None:
        raise NotImplementedError


class AbstractUnitOfWork(abc.ABC):
    session_states: AbstractSessionStateRepository
    draft_sessions: AbstractDraftSessionRepository

    @abc.abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.commit()
            return
        self.rollback()

    @abc.abstractmethod
    def commit(self) -> None:
        raise NotImplementedError
