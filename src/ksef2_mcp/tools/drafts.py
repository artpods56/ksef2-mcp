from json import JSONDecodeError, loads
from typing import Annotated, Literal
from uuid import UUID

from fastmcp.tools.function_tool import tool
from pydantic import BaseModel, Field, field_validator

from ksef2_mcp.domain.outputs import (
    BuildDraftResult,
    CreateDraftResult,
    DeleteDraftResult,
    DraftContextsResult,
    DraftPossibleMethodsResult,
    UpdateDraftResult,
)
from ksef2_mcp.services.drafts import (
    CallOperation,
    DoneOperation,
    RuntimeOperation,
    SpawnOperation,
    get_draft_runtime_service,
)

DraftTypeValue = Annotated[
    Literal["standard_invoice"],
    Field(
        description=(
            "Root draft type to create. Start with 'standard_invoice' for the "
            "nested FA(3) invoice builder runtime."
        ),
        examples=["standard_invoice"],
    ),
]

DraftId = Annotated[
    UUID,
    Field(
        description="Identifier of an existing draft runtime session.",
        examples=["2f1c3dbe-6e5a-4f8b-a9b7-d2d5f1b2a123"],
    ),
]

ContextId = Annotated[
    str,
    Field(
        description="Identifier of an active builder context inside a draft.",
        examples=["root", "payment_1", "rows_1"],
        min_length=1,
    ),
]

BuildOutputFormat = Annotated[
    Literal["xml", "model", "spec"],
    Field(
        description="Output shape returned by build_draft.",
        examples=["xml", "model", "spec"],
        default="xml",
    ),
]


class DraftOperationInput(BaseModel):
    op_id: str | None = Field(
        default=None,
        description=(
            "Optional client-side identifier used to correlate operation results."
        ),
    )
    op: Literal["spawn", "call", "done"] = Field(
        description="Runtime operation kind.",
    )
    context_id: str = Field(
        description="Existing context to operate on.",
        min_length=1,
    )
    method: str = Field(
        description="Method name to invoke on the context.",
        min_length=1,
    )
    new_context_id: str | None = Field(
        default=None,
        description="Required for spawn operations; ignored for call and done.",
    )
    args: dict[str, object] | None = Field(
        default=None,
        description="Method payload keyed by argument name.",
    )

    @field_validator("args", mode="before")
    @classmethod
    def _parse_json_args(cls, value: object) -> object:
        if value is None or isinstance(value, dict):
            return value
        if not isinstance(value, str):
            return value

        try:
            parsed = loads(value)
        except JSONDecodeError as exc:
            raise ValueError(
                "args must be a dictionary or a JSON object string."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError(
                "args JSON string must decode to an object."
            )

        return parsed

    def to_runtime_operation(self) -> RuntimeOperation:
        match self.op:
            case "spawn":
                if not self.new_context_id:
                    raise ValueError("new_context_id is required for spawn operations.")
                return SpawnOperation(
                    op_id=self.op_id,
                    context_id=self.context_id,
                    method=self.method,
                    new_context_id=self.new_context_id,
                    args=self.args,
                )
            case "call":
                return CallOperation(
                    op_id=self.op_id,
                    context_id=self.context_id,
                    method=self.method,
                    args=self.args,
                )
            case "done":
                return DoneOperation(
                    op_id=self.op_id,
                    context_id=self.context_id,
                    method=self.method,
                )
            case _:
                raise ValueError(f"Unsupported operation {self.op!r}")


@tool(
    name="create_draft",
    description=(
        "Create a new nested builder draft runtime and register the root context."
    ),
)
def create_draft(draft_type: DraftTypeValue = "standard_invoice") -> CreateDraftResult:
    return get_draft_runtime_service().create_draft(draft_type)


@tool(
    name="get_contexts",
    description=(
        "List the active builder contexts for a draft, including parent-child links."
    ),
)
def get_contexts(draft_id: DraftId) -> DraftContextsResult:
    return get_draft_runtime_service().get_contexts(draft_id)


@tool(
    name="get_possible_methods",
    description=(
        "Inspect the methods currently available on a specific draft context and "
        "return their payload schemas."
    ),
)
def get_possible_methods(
    draft_id: DraftId,
    context_id: ContextId,
) -> DraftPossibleMethodsResult:
    return get_draft_runtime_service().get_possible_methods(draft_id, context_id)


@tool(
    name="update_draft",
    description=(
        "Apply a batch of spawn, call, and done operations to the nested "
        "builder runtime."
    ),
)
def update_draft(
    draft_id: DraftId,
    operations: list[DraftOperationInput],
) -> UpdateDraftResult:
    return get_draft_runtime_service().update_draft(
        draft_id,
        [operation.to_runtime_operation() for operation in operations],
    )


@tool(
    name="build_draft",
    description=(
        "Build the root draft and return XML, a domain-model dump, or a spec dump."
    ),
)
def build_draft(
    draft_id: DraftId,
    output_format: BuildOutputFormat = "xml",
) -> BuildDraftResult:
    return get_draft_runtime_service().build_draft(
        draft_id,
        output_format=output_format,
    )


@tool(
    name="delete_draft",
    description=("Delete a draft runtime and all active contexts tracked for it."),
)
def delete_draft(draft_id: DraftId) -> DeleteDraftResult:
    return get_draft_runtime_service().delete_draft(draft_id)
