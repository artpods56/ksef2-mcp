from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast

from ksef2 import FormSchema
from ksef2.domain.models.session import OnlineSessionState

from ksef2_mcp import errors
from ksef2_mcp.services.authenticated_client import AuthenticatedClientFactory
from ksef2_mcp.services.sessions import LocalSessionService
from ksef2_mcp.adapters.uow import _SHARED_SESSION_STATES


def build_session_state(reference_number: str) -> OnlineSessionState:
    return OnlineSessionState(
        reference_number=reference_number,
        aes_key="YWVzLWtleQ==",
        iv="aXYta2V5",
        access_token="access-token",
        form_code=FormSchema.FA3,
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )


def test_local_session_service_open_and_list_sessions() -> None:
    _SHARED_SESSION_STATES.clear()
    session_states = [
        build_session_state("SESSION-1"),
        build_session_state("SESSION-2"),
    ]

    class StubFactory:
        def __init__(self) -> None:
            self.calls = 0

        @contextmanager
        def create(self):
            session_state = session_states[self.calls]
            self.calls += 1
            yield SimpleNamespace(
                online_session=lambda *, form_code: SimpleNamespace(
                    get_state=lambda: session_state,
                )
            )

    service = LocalSessionService(
        client_factory=cast(AuthenticatedClientFactory, StubFactory())
    )

    first = service.open_interactive_session(FormSchema.FA3)
    second = service.open_interactive_session(FormSchema.FA3)
    listed = service.list_interactive_sessions()

    assert first.uuid != second.uuid
    assert [session.reference_number for session in listed] == [
        "SESSION-1",
        "SESSION-2",
    ]


def test_local_session_service_closes_online_session(monkeypatch) -> None:
    _SHARED_SESSION_STATES.clear()
    session_state = build_session_state("SESSION-1")
    transport_marker = object()

    class StubFactory:
        @contextmanager
        def create(self):
            yield SimpleNamespace(
                _authed_transport=transport_marker,
                online_session=lambda *, form_code: SimpleNamespace(
                    get_state=lambda: session_state,
                ),
            )

    service = LocalSessionService(
        client_factory=cast(AuthenticatedClientFactory, StubFactory())
    )
    session_handle = service.open_interactive_session(FormSchema.FA3)

    seen = {}

    class StubOnlineSessionClient:
        def __init__(self, *, transport, state):
            seen["transport"] = transport
            seen["state"] = state

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(
        "ksef2_mcp.services.sessions.OnlineSessionClient",
        StubOnlineSessionClient,
    )

    service.close_interactive_session(session_handle.uuid)

    listed = service.list_interactive_sessions()

    assert seen == {
        "transport": transport_marker,
        "state": session_state,
        "closed": True,
    }
    assert listed == []


def test_local_session_service_preserves_configuration_errors() -> None:
    class StubFactory:
        @contextmanager
        def create(self):
            raise errors.ConfigurationError("NIP has not been configured.")
            yield

    service = LocalSessionService(
        client_factory=cast(AuthenticatedClientFactory, StubFactory())
    )

    try:
        service.open_interactive_session(FormSchema.FA3)
    except errors.ConfigurationError as exc:
        assert exc.message == "NIP has not been configured."
    else:
        raise AssertionError("ConfigurationError was not propagated")
