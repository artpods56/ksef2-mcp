from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

type DraftType = Literal["standard_invoice"]
from ksef2.services.builders.fa3.root import StandardInvoiceBuilder

@dataclass(slots=True)
class DraftContext:
    context_id: str
    builder: StandardInvoiceBuilder
    parent_context_id: str | None = None
    opened_via_method: str | None = None

    @property
    def builder_type(self) -> str:
        builder_type = type(self.builder)
        return f"{builder_type.__module__}.{builder_type.__qualname__}"


@dataclass(slots=True)
class DraftSession:
    draft_id: UUID
    draft_type: DraftType
    contexts: dict[str, DraftContext] = field(default_factory=dict)
