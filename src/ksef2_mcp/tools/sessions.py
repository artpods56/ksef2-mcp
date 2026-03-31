from collections.abc import Sequence
from typing import Annotated, Literal
from uuid import UUID

from fastmcp.tools.function_tool import tool
from mcp.types import ToolAnnotations

from ksef2 import FormSchema

from ksef2_mcp.domain.models import SessionHandle
from ksef2_mcp.services.sessions import get_session_service

type FormCode = Literal["FA2", "FA3", "PEF3", "PEF_KOR3"]


@tool(
    name="open_interactive_session",
    description="Open a new interactive session for the given form code.",
)
def open_interactive_session(
    form_code: Annotated[FormCode, "Form code for the interactive session"],
) -> SessionHandle:
    return get_session_service().open_interactive_session(
        form_code=FormSchema[form_code],
    )


@tool(
    name="close_interactive_session",
    description="Close an interactive session by its handle.",
    annotations=ToolAnnotations(
        destructiveHint=True,
    ),
)
def close_interactive_session(
    session_handle: Annotated[UUID, "Session handle"],
) -> None:
    return get_session_service().close_interactive_session(
        session_id=session_handle,
    )


@tool(
    name="list_interactive_sessions",
    description="List all currently open interactive sessions.",
    annotations=ToolAnnotations(
        readOnlyHint=True,
    ),
)
def list_interactive_sessions() -> Sequence[SessionHandle]:
    return get_session_service().list_interactive_sessions()
