from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from ksef2.core.exceptions import KSeFSessionError
from ksef2.domain.models.session import (
    FormSchema,
    InvoiceStatusInfo,
    OnlineSessionState,
    SessionInvoiceStatusResponse,
)
from pydantic import AnyUrl

from ksef2_mcp.adapters.database.session import get_session_factory
from ksef2_mcp.adapters.database.uow import SqlAlchemyUnitOfWork
from ksef2_mcp.config import AppSettings
from ksef2_mcp.domain.enums import InvoiceStatus, SubmissionStatus
from ksef2_mcp.errors import (
    InvalidInputError,
    ResourceNotFoundError,
    SessionExpiredError,
)
from ksef2_mcp.services.authenticated_client import AuthenticatedClientFactory
from ksef2_mcp.services.invoices import InvoiceService


def build_session_state() -> OnlineSessionState:
    return OnlineSessionState(
        reference_number="SESSION-1",
        aes_key="YWVzLWtleQ==",
        iv="aXYta2V5",
        access_token="access-token",
        form_code=FormSchema.FA3,
        valid_until=datetime.now(UTC) + timedelta(hours=1),
    )


def build_status(
    *,
    reference_number: str = "INV-REF-1",
    code: int = 100,
    description: str = "Processing",
    ksef_number: str | None = None,
) -> SessionInvoiceStatusResponse:
    return SessionInvoiceStatusResponse(
        ordinal_number=1,
        reference_number=reference_number,
        invoice_hash="hash",
        invoicing_date=datetime.now(UTC),
        ksef_number=ksef_number,
        upo_download_url=(
            cast(AnyUrl, "https://example.com/upo.xml") if ksef_number else None
        ),
        status=InvoiceStatusInfo(code=code, description=description),
    )


def build_service(*, tmp_path: Path, factory) -> InvoiceService:
    settings = AppSettings(
        nip="5261040828",
        state_db_path=tmp_path / "state.sqlite3",
        workspace_id="workspace-1",
        user_id="user-1",
    )
    session_factory = get_session_factory(settings.state_db_path)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return InvoiceService(
        client_factory=cast(AuthenticatedClientFactory, factory),
        uow_factory=uow_factory,
        settings=settings,
    )


class UnusedFactory:
    @contextmanager
    def create(self):
        raise AssertionError("client factory should not be used")
        yield


def test_upload_invoice_xml_persists_valid_document(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())

    result = service.upload_invoice_xml(valid_fa3_invoice_xml)
    with service._uow_factory() as uow:  # pyright: ignore[reportPrivateUsage]
        stored = uow.invoices.get(result.invoice_id)

    assert result.status is InvoiceStatus.UPLOADED
    assert stored is not None
    assert stored.invoice_xml == valid_fa3_invoice_xml
    assert stored.status is InvoiceStatus.UPLOADED


def test_upload_invoice_xml_rejects_malformed_xml(tmp_path: Path) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())

    with pytest.raises(InvalidInputError, match="not well-formed"):
        service.upload_invoice_xml("<Faktura>")

    with service._uow_factory() as uow:  # pyright: ignore[reportPrivateUsage]
        assert uow.invoices.list_all() == []


def test_upload_invoice_xml_rejects_non_fa3_xml(tmp_path: Path) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())

    with pytest.raises(InvalidInputError, match="valid FA\\(3\\)"):
        service.upload_invoice_xml("<root />")

    with service._uow_factory() as uow:  # pyright: ignore[reportPrivateUsage]
        assert uow.invoices.list_all() == []


def test_send_invoice_submits_stored_xml(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    session_state = build_session_state()

    class StubSession:
        def send_invoice(self, *, invoice_xml):
            assert invoice_xml == valid_fa3_invoice_xml.encode("utf-8")
            return SimpleNamespace(reference_number="INV-REF-1")

        def get_state(self):
            return session_state

    class StubFactory:
        @contextmanager
        def create(self):
            yield SimpleNamespace(online_session=lambda *, form_code: StubSession())

    service = build_service(tmp_path=tmp_path, factory=StubFactory())
    upload = service.upload_invoice_xml(valid_fa3_invoice_xml)

    result = service.send_invoice(upload.invoice_id)
    with service._uow_factory() as uow:  # pyright: ignore[reportPrivateUsage]
        stored_invoice = uow.invoices.get(upload.invoice_id)
        stored_submission = uow.submissions.get(result.submission_id)

    assert result.invoice_id == upload.invoice_id
    assert result.status is SubmissionStatus.SUBMITTED
    assert stored_invoice is not None
    assert stored_invoice.status is InvoiceStatus.SUBMITTED
    assert stored_submission is not None
    assert stored_submission.invoice_reference_number == "INV-REF-1"
    assert stored_submission.session_state_json is not None


def test_send_invoice_reuses_active_submission(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    session_state = build_session_state()
    factory_calls = 0

    class StubSession:
        def send_invoice(self, *, invoice_xml):
            return SimpleNamespace(reference_number="INV-REF-1")

        def get_state(self):
            return session_state

    class StubFactory:
        @contextmanager
        def create(self):
            nonlocal factory_calls
            factory_calls += 1
            yield SimpleNamespace(online_session=lambda *, form_code: StubSession())

    service = build_service(tmp_path=tmp_path, factory=StubFactory())
    upload = service.upload_invoice_xml(valid_fa3_invoice_xml)

    first = service.send_invoice(upload.invoice_id)
    second = service.send_invoice(upload.invoice_id)

    assert first.submission_id == second.submission_id
    assert second.status is SubmissionStatus.SUBMITTED
    assert factory_calls == 1


def test_get_submission_status_finalizes_submission_and_invoice(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    session_state = build_session_state()
    final_status = build_status(
        code=200,
        description="Accepted",
        ksef_number="KSEF-123",
    )

    class SendSession:
        def send_invoice(self, *, invoice_xml):
            return SimpleNamespace(reference_number="INV-REF-1")

        def get_state(self):
            return session_state

    class ResumeSession:
        closed = False

        def get_invoice_status(self, *, invoice_reference_number):
            assert invoice_reference_number == "INV-REF-1"
            return final_status

        def close(self):
            self.closed = True

    resume_session = ResumeSession()

    class StubFactory:
        def __init__(self) -> None:
            self.calls = 0

        @contextmanager
        def create(self):
            self.calls += 1
            if self.calls == 1:
                yield SimpleNamespace(online_session=lambda *, form_code: SendSession())
                return
            yield SimpleNamespace(
                resume_online_session=lambda state: resume_session,
            )

    factory = StubFactory()
    service = build_service(tmp_path=tmp_path, factory=factory)
    upload = service.upload_invoice_xml(valid_fa3_invoice_xml)
    submission = service.send_invoice(upload.invoice_id)

    result = service.get_submission_status(submission.submission_id)
    with service._uow_factory() as uow:  # pyright: ignore[reportPrivateUsage]
        stored_invoice = uow.invoices.get(upload.invoice_id)
        stored_submission = uow.submissions.get(submission.submission_id)

    assert result.status is SubmissionStatus.ACCEPTED
    assert result.ksef_number == "KSEF-123"
    assert resume_session.closed is True
    assert stored_invoice is not None
    assert stored_invoice.status is InvoiceStatus.ACCEPTED
    assert stored_submission is not None
    assert stored_submission.session_state_json is None
    assert stored_submission.finalized_at is not None


def test_get_submission_status_missing_submission_raises_not_found(
    tmp_path: Path,
) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())

    with pytest.raises(ResourceNotFoundError, match="No stored submission"):
        service.get_submission_status("missing")


def test_get_submission_status_expired_session_raises_error(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    session_state = build_session_state()

    class SendSession:
        def send_invoice(self, *, invoice_xml):
            return SimpleNamespace(reference_number="INV-REF-1")

        def get_state(self):
            return session_state

    class ResumeSession:
        def get_invoice_status(self, *, invoice_reference_number):
            raise KSeFSessionError("session expired")

    class StubFactory:
        def __init__(self) -> None:
            self.calls = 0

        @contextmanager
        def create(self):
            self.calls += 1
            if self.calls == 1:
                yield SimpleNamespace(online_session=lambda *, form_code: SendSession())
                return
            yield SimpleNamespace(
                resume_online_session=lambda state: ResumeSession(),
            )

    service = build_service(tmp_path=tmp_path, factory=StubFactory())
    upload = service.upload_invoice_xml(valid_fa3_invoice_xml)
    submission = service.send_invoice(upload.invoice_id)

    with pytest.raises(SessionExpiredError, match="no longer resumable"):
        service.get_submission_status(submission.submission_id)


def test_get_invoice_returns_raw_xml(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())
    upload = service.upload_invoice_xml(valid_fa3_invoice_xml)

    result = service.get_invoice(upload.invoice_id)

    assert result.invoice_id == upload.invoice_id
    assert result.invoice_xml == valid_fa3_invoice_xml
    assert result.status is InvoiceStatus.UPLOADED


def test_list_invoices_returns_minimal_metadata(
    tmp_path: Path, valid_fa3_invoice_xml: str
) -> None:
    service = build_service(tmp_path=tmp_path, factory=UnusedFactory())
    first = service.upload_invoice_xml(valid_fa3_invoice_xml)
    second = service.upload_invoice_xml(valid_fa3_invoice_xml)

    result = service.list_invoices()

    assert [invoice.invoice_id for invoice in result.invoices] == [
        second.invoice_id,
        first.invoice_id,
    ]
    assert all(invoice.status is InvoiceStatus.UPLOADED for invoice in result.invoices)
