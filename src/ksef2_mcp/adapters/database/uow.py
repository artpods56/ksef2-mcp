from types import TracebackType
from typing import Callable, Self, final, override

from sqlalchemy.orm import Session, sessionmaker

from ksef2_mcp.adapters.database import get_session_factory, repository
from ksef2_mcp.adapters.draft_store import (
    _SHARED_DRAFT_STATES,
    InMemoryDraftSessionRepository,
)
from ksef2_mcp.ports.repository import AbstractUnitOfWork


@final
class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self.session: Session
        self._committed = False

    @override
    def __enter__(self) -> Self:
        self.session = self.session_factory()
        self._committed = False
        self.session_states = repository.SQLAlchemySessionStateRepository(self.session)
        self.draft_sessions = InMemoryDraftSessionRepository(_SHARED_DRAFT_STATES)
        self.invoices = repository.SQLAlchemyInvoiceRepository(self.session)
        self.submissions = repository.SQLAlchemySubmissionRepository(self.session)
        return self

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        elif not self._committed and (
            self.session.new or self.session.dirty or self.session.deleted
        ):
            self.rollback()
        self.session.close()

    @override
    def commit(self) -> None:
        self.session.commit()
        self._committed = True

    @override
    def rollback(self) -> None:
        self.session.rollback()


UnitOfWorkFactory = Callable[[], AbstractUnitOfWork]


def fresh_uow() -> AbstractUnitOfWork:
    from ksef2_mcp.config import get_app_settings

    return SqlAlchemyUnitOfWork(
        session_factory=get_session_factory(get_app_settings().state_db_path)
    )
