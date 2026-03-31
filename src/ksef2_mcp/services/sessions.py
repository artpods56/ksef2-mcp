import abc
from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from ksef2 import FormSchema
from ksef2.domain.models import OnlineSessionState

from ksef2_mcp import errors
from ksef2_mcp.domain.models import SessionHandle
from ksef2_mcp.services.authenticated_client import (
    AuthenticatedClientFactory,
    get_authenticated_client_factory,
)
from ksef2_mcp.adapters.uow import fresh_uow


class BaseSessionService(abc.ABC):
    def __init__(self, client_factory: AuthenticatedClientFactory):
        self._client_factory = client_factory

    @abc.abstractmethod
    def open_interactive_session(self, form_code: FormSchema):
        raise NotImplementedError()

    @abc.abstractmethod
    def close_interactive_session(self, session_id: UUID):
        raise NotImplementedError()

    @abc.abstractmethod
    def list_interactive_sessions(self) -> Sequence[SessionHandle]:
        raise NotImplementedError()


class LocalSessionService(BaseSessionService):
    def __init__(self, client_factory: AuthenticatedClientFactory):
        super().__init__(client_factory)

    def open_interactive_session(self, form_code: FormSchema) -> SessionHandle:
        try:
            with self._client_factory.create() as client:
                with fresh_uow() as uow:
                    session_state = client.online_session(
                        form_code=form_code
                    ).get_state()

                    session_handle = SessionHandle(state=session_state)

                    uow.session_states.add_state(session_handle)

                    return session_handle
        except Exception as exc:
            raise errors.SessionManagementError(
                "Failed to open interactive session"
            ) from exc

    def close_interactive_session(self, session_id: UUID):
        try:
            with self._client_factory.create() as client:
                with fresh_uow() as uow:
                    session_handle = uow.session_states.get_state_or_raise(session_id)
                    if not isinstance(session_handle.state, OnlineSessionState):
                        raise ValueError(
                            "Interactive close is only supported for online sessions"
                        )

                    session = client.resume_online_session(session_handle.state)
                    session.close()
                    session_handle.close()

        except Exception as exc:
            raise errors.SessionManagementError(
                "Failed to close interactive session"
            ) from exc

    def list_interactive_sessions(self) -> Sequence[SessionHandle]:
        try:
            with fresh_uow() as uow:
                return [
                    session_handle
                    for session_handle in uow.session_states.list_all()
                    if session_handle.is_open
                ]
        except Exception:
            raise errors.SessionManagementError(
                "Failed to list all interactive sessions"
            )


@lru_cache(maxsize=1)
def get_session_service() -> LocalSessionService:
    return LocalSessionService(
        client_factory=get_authenticated_client_factory(),
    )
