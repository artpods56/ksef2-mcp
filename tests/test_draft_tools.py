from uuid import uuid4

from ksef2_mcp.domain.outputs import CreateDraftResult, UpdateDraftResult
from ksef2_mcp.services.drafts import SpawnOperation
from ksef2_mcp.tools.drafts import DraftOperationInput, create_draft, update_draft


def test_create_draft_tool_delegates_to_service(monkeypatch) -> None:
    expected = CreateDraftResult(
        draft_id=uuid4(),
        draft_type="standard_invoice",
        root_context_id="root",
    )

    class StubService:
        def create_draft(self, draft_type):
            assert draft_type == "standard_invoice"
            return expected

    monkeypatch.setattr(
        "ksef2_mcp.tools.drafts.get_draft_runtime_service",
        lambda: StubService(),
    )

    assert create_draft() == expected


def test_update_draft_tool_serializes_operation_models(monkeypatch) -> None:
    expected = UpdateDraftResult(
        draft_id=uuid4(),
        draft_type="standard_invoice",
        operations=[],
        contexts=[],
    )
    seen = {}

    class StubService:
        def update_draft(self, draft_id, operations):
            seen["draft_id"] = draft_id
            seen["operations"] = operations
            return expected

    monkeypatch.setattr(
        "ksef2_mcp.tools.drafts.get_draft_runtime_service",
        lambda: StubService(),
    )

    draft_id = uuid4()
    result = update_draft(
        draft_id=draft_id,
        operations=[
            DraftOperationInput(
                op_id="op-1",
                op="spawn",
                context_id="root",
                method="standard",
                new_context_id="body_1",
            )
        ],
    )

    assert result == expected
    assert seen["draft_id"] == draft_id
    assert seen["operations"] == [
        SpawnOperation(
            op_id="op-1",
            context_id="root",
            method="standard",
            new_context_id="body_1",
            args=None,
        )
    ]


def test_update_draft_tool_accepts_json_string_args(monkeypatch) -> None:
    expected = UpdateDraftResult(
        draft_id=uuid4(),
        draft_type="standard_invoice",
        operations=[],
        contexts=[],
    )
    seen = {}

    class StubService:
        def update_draft(self, draft_id, operations):
            seen["draft_id"] = draft_id
            seen["operations"] = operations
            return expected

    monkeypatch.setattr(
        "ksef2_mcp.tools.drafts.get_draft_runtime_service",
        lambda: StubService(),
    )

    draft_id = uuid4()
    result = update_draft(
        draft_id=draft_id,
        operations=[
            DraftOperationInput(
                op_id="op-1",
                op="call",
                context_id="root",
                method="header",
                args='{"system_info":"codex-ksef-mcp"}',
            )
        ],
    )

    assert result == expected
    assert seen["draft_id"] == draft_id
    assert seen["operations"][0].args == {"system_info": "codex-ksef-mcp"}
