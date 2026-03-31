from typing import Sequence
from uuid import UUID

from ksef2_mcp.domain.models import InvoiceBuilderHandle
from ksef2_mcp.ports.repository import AbstractInvoiceBuilderRepository


class InMemoryInvoiceBuilderRepository(AbstractInvoiceBuilderRepository):
    def __init__(self, builders: dict[UUID, InvoiceBuilderHandle] | None = None):
        self._builders = {} if builders is None else builders

    def add_builder(self, builder: InvoiceBuilderHandle) -> None:
        self._builders[builder.uuid] = builder

    def get_builder(self, uuid: UUID) -> InvoiceBuilderHandle | None:
        return self._builders.get(uuid)

    def get_builder_or_raise(self, uuid: UUID) -> InvoiceBuilderHandle:
        builder = self.get_builder(uuid)
        if builder is None:
            raise ValueError(f"No invoice builder state with UUID {uuid} found")
        return builder

    def list_all(self) -> Sequence[UUID]:
        return list(self._builders.keys())
