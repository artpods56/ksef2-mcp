from collections.abc import Sequence
from typing import final, override
from uuid import UUID

from ksef2_mcp.domain.drafts import DraftSession
from ksef2_mcp.ports.repository import AbstractDraftSessionRepository

type DraftState = dict[UUID, DraftSession]

_SHARED_DRAFT_STATES: DraftState = {}


@final
class InMemoryDraftSessionRepository(AbstractDraftSessionRepository):
    def __init__(self, drafts: dict[UUID, DraftSession] | None = None):
        self._drafts = {} if drafts is None else drafts

    @override
    def add(self, draft_session: DraftSession) -> None:
        self._drafts[draft_session.draft_id] = draft_session

    @override
    def get(self, draft_id: UUID) -> DraftSession | None:
        return self._drafts.get(draft_id)

    @override
    def get_or_raise(self, draft_id: UUID) -> DraftSession:
        draft_session = self.get(draft_id)
        if draft_session is None:
            raise ValueError(f"No draft session with UUID {draft_id} found")
        return draft_session

    @override
    def delete(self, draft_id: UUID) -> bool:
        return self._drafts.pop(draft_id, None) is not None

    @override
    def list_all(self) -> Sequence[DraftSession]:
        return list(self._drafts.values())
