from ksef2 import FormSchema
from pydantic import TypeAdapter

from ksef2_mcp.tools import sessions as sessions_module


def test_form_code_schema_is_string_enum() -> None:
    schema = TypeAdapter(sessions_module.FormCode).json_schema()

    assert schema == {
        "enum": ["FA2", "FA3", "PEF3", "PEF_KOR3"],
        "type": "string",
    }


def test_open_interactive_session_maps_form_code_to_sdk_enum(monkeypatch) -> None:
    expected = object()
    seen = {}

    class StubService:
        def open_interactive_session(self, form_code):
            seen["form_code"] = form_code
            return expected

    monkeypatch.setattr(
        sessions_module,
        "get_session_service",
        lambda: StubService(),
    )

    result = sessions_module.open_interactive_session(form_code="FA3")

    assert result is expected
    assert seen["form_code"] is FormSchema.FA3


def test_open_interactive_session_accepts_parenthesized_alias(monkeypatch) -> None:
    expected = object()
    seen = {}

    class StubService:
        def open_interactive_session(self, form_code):
            seen["form_code"] = form_code
            return expected

    monkeypatch.setattr(
        sessions_module,
        "get_session_service",
        lambda: StubService(),
    )

    result = sessions_module.open_interactive_session(form_code="FA(3)")

    assert result is expected
    assert seen["form_code"] is FormSchema.FA3
