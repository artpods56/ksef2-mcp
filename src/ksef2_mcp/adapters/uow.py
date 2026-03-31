import copy
from types import TracebackType
from typing import Self, final, override, TypedDict
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from ksef2_mcp.adapters.database import repository as database_repository
from ksef2_mcp.adapters.database.repository import InMemorySessionStateRepository
from ksef2_mcp.adapters.adapters import InMemoryInvoiceBuilderRepository
from ksef2_mcp.domain.models import SessionHandle, InvoiceBuilderHandle
from ksef2_mcp.ports.repository import AbstractUnitOfWork


@final
class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self.session: Session

    @override
    def __enter__(self) -> Self:
        self.session = self.session_factory()
        self.session_states = database_repository.SQLAlchemySessionStateRepository(
            self.session
        )

        return self

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.session.close()

    @override
    def commit(self) -> None:
        self.session.commit()

    @override
    def rollback(self) -> None:
        self.session.rollback()


type SessionState = dict[UUID, SessionHandle]
type InvoiceBuilderState = dict[UUID, InvoiceBuilderHandle]


class InMemoryStore(TypedDict):
    sessions: SessionState
    builders: InvoiceBuilderState


_SHARED_IN_MEMORY_STORE: InMemoryStore = {
    "sessions": {},
    "builders": {},
}
_SHARED_SESSION_STATES = _SHARED_IN_MEMORY_STORE["sessions"]
_SHARED_IN_MEMORY_BUILDERS = _SHARED_IN_MEMORY_STORE["builders"]


@final
class InMemoryUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        self._backup_store: InMemoryStore | None = None
        self.session_states: InMemorySessionStateRepository = (
            InMemorySessionStateRepository(_SHARED_IN_MEMORY_STORE["sessions"])
        )
        self.invoice_builders: InMemoryInvoiceBuilderRepository = (
            InMemoryInvoiceBuilderRepository(_SHARED_IN_MEMORY_STORE["builders"])
        )

    @override
    def __enter__(self):
        self._backup_store = copy.deepcopy(_SHARED_IN_MEMORY_STORE)
        return self

    @override
    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)

    @override
    def commit(self):
        if self._backup_store is None:
            raise RuntimeError("Cannot commit without entering the context")
        self._backup_store = None

    @override
    def rollback(self):
        if self._backup_store is None:
            raise RuntimeError("Cannot rollback without entering the context")
        _SHARED_IN_MEMORY_STORE["sessions"].clear()
        _SHARED_IN_MEMORY_STORE["builders"].clear()
        _SHARED_IN_MEMORY_STORE.update(copy.deepcopy(self._backup_store))
        self._backup_store = None


def fresh_uow() -> AbstractUnitOfWork:
    return InMemoryUnitOfWork()
