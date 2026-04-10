import inspect
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Any, Literal, get_type_hints
from uuid import UUID, uuid4

from ksef2.fa3 import FA3InvoiceBuilder
from pydantic import ValidationError

from ksef2_mcp import errors
from ksef2_mcp.adapters.uow import fresh_uow
from ksef2_mcp.domain.drafts import DraftContext, DraftSession, DraftType
from ksef2_mcp.domain.outputs import (
    BuildDraftResult,
    CreateDraftResult,
    DeleteDraftResult,
    DraftContextResult,
    DraftContextsResult,
    DraftMethodResult,
    DraftOperationResult,
    DraftPossibleMethodsResult,
    UpdateDraftResult,
)
from ksef2_mcp.ports.repository import AbstractUnitOfWork
from ksef2_mcp.services.annotations import (
    get_method_payload_json_schema,
    get_method_payload_model,
)


class DraftOperationType(StrEnum):
    SPAWN = "spawn"
    CALL = "call"
    DONE = "done"


_ROOT_CONTEXT_ID = "root"
_EXCLUDED_METHODS = {
    "build",
    "dump_state",
    "dump_state_json",
    "from_invoice",
    "from_model",
    "from_state",
    "from_state_json",
    "load_state",
    "to_spec",
    "to_xml",
}


@lru_cache(maxsize=1)
def _draft_factories() -> dict[DraftType, type[FA3InvoiceBuilder]]:
    return {
        "standard_invoice": FA3InvoiceBuilder,
    }


@dataclass(slots=True, kw_only=True)
class DraftOperation:
    context_id: str
    method: str
    op_id: str | None = None

    @property
    def op(self) -> DraftOperationType:
        raise NotImplementedError


@dataclass(slots=True, kw_only=True)
class SpawnOperation(DraftOperation):
    new_context_id: str
    args: dict[str, Any] | None = None

    @property
    def op(self) -> DraftOperationType:
        return DraftOperationType.SPAWN


@dataclass(slots=True, kw_only=True)
class CallOperation(DraftOperation):
    args: dict[str, Any] | None = None

    @property
    def op(self) -> DraftOperationType:
        return DraftOperationType.CALL


@dataclass(slots=True, kw_only=True)
class DoneOperation(DraftOperation):
    @property
    def op(self) -> DraftOperationType:
        return DraftOperationType.DONE


type RuntimeOperation = SpawnOperation | CallOperation | DoneOperation


class DraftRuntimeService:
    def __init__(
        self,
        uow_factory: Callable[[], AbstractUnitOfWork] = fresh_uow,
    ) -> None:
        self._uow_factory = uow_factory

    def create_draft(self, draft_type: DraftType) -> CreateDraftResult:
        factory = _draft_factories().get(draft_type)
        if factory is None:
            raise errors.InvalidInputError(
                f"Unsupported draft_type {draft_type!r}. "
                "Supported values include: standard_invoice"
            )

        draft_id = uuid4()
        root_builder = factory()
        session = DraftSession(
            draft_id=draft_id,
            draft_type=draft_type,
            contexts={
                _ROOT_CONTEXT_ID: DraftContext(
                    context_id=_ROOT_CONTEXT_ID,
                    builder=root_builder,
                )
            },
        )
        with self._uow_factory() as uow:
            uow.draft_sessions.add(session)

        return CreateDraftResult(
            draft_id=draft_id,
            draft_type=draft_type,
            root_context_id=_ROOT_CONTEXT_ID,
        )

    def get_contexts(self, draft_id: UUID) -> DraftContextsResult:
        with self._uow_factory() as uow:
            session = self._get_session_or_raise(uow, draft_id)
            return DraftContextsResult(
                draft_id=session.draft_id,
                draft_type=session.draft_type,
                contexts=self._serialize_contexts(session),
            )

    def get_possible_methods(
        self,
        draft_id: UUID,
        context_id: str,
    ) -> DraftPossibleMethodsResult:
        with self._uow_factory() as uow:
            session = self._get_session_or_raise(uow, draft_id)
            context = self._get_context_or_raise(session, context_id)

            methods = []
            for method_name in self._iter_method_names(context.builder):
                bound_method = getattr(context.builder, method_name)
                methods.append(
                    DraftMethodResult(
                        name=method_name,
                        operation_type=self._classify_method(bound_method).value,
                        payload_schema=get_method_payload_json_schema(
                            bound_method,
                            include_extras=True,
                        ),
                    )
                )

            methods.sort(key=lambda item: (item.operation_type, item.name))

            return DraftPossibleMethodsResult(
                draft_id=session.draft_id,
                context_id=context.context_id,
                builder_type=context.builder_type,
                methods=methods,
            )

    def update_draft(
        self,
        draft_id: UUID,
        operations: list[RuntimeOperation],
    ) -> UpdateDraftResult:
        with self._uow_factory() as uow:
            session = self._get_session_or_raise(uow, draft_id)
            results: list[DraftOperationResult] = []

            for index, operation in enumerate(operations):
                try:
                    match operation:
                        case SpawnOperation():
                            self._spawn(
                                session,
                                context_id=operation.context_id,
                                method_name=operation.method,
                                new_context_id=operation.new_context_id,
                                args=operation.args,
                            )
                        case CallOperation():
                            self._call(
                                session,
                                context_id=operation.context_id,
                                method_name=operation.method,
                                args=operation.args,
                            )
                        case DoneOperation():
                            self._done(
                                session,
                                context_id=operation.context_id,
                                method_name=operation.method,
                            )
                        case _:
                            raise errors.InvalidInputError(
                                f"Unsupported runtime operation {type(operation)!r}."
                            )

                    results.append(
                        DraftOperationResult(
                            op_index=index,
                            op_id=operation.op_id,
                            op=operation.op.value,
                            context_id=operation.context_id,
                            method=operation.method,
                            new_context_id=operation.new_context_id
                            if isinstance(operation, SpawnOperation)
                            else None,
                            status="succeeded",
                        )
                    )
                except errors.KsefMcpError as exc:
                    results.append(
                        DraftOperationResult(
                            op_index=index,
                            op_id=operation.op_id,
                            op=operation.op.value,
                            context_id=operation.context_id,
                            method=operation.method,
                            new_context_id=operation.new_context_id
                            if isinstance(operation, SpawnOperation)
                            else None,
                            status="failed",
                            message=exc.message,
                            error_code=exc.code,
                        )
                    )

            return UpdateDraftResult(
                draft_id=session.draft_id,
                draft_type=session.draft_type,
                operations=results,
                contexts=self._serialize_contexts(session),
            )

    def build_draft(
        self,
        draft_id: UUID,
        *,
        output_format: Literal["xml", "model", "spec"] = "xml",
    ) -> BuildDraftResult:
        with self._uow_factory() as uow:
            session = self._get_session_or_raise(uow, draft_id)
            root_context = self._get_context_or_raise(session, _ROOT_CONTEXT_ID)
            root_builder = root_context.builder

            try:
                match output_format:
                    case "xml":
                        content: Any = root_builder.to_xml()
                    case "model":
                        content = root_builder.build().model_dump(mode="json")
                    case "spec":
                        spec = root_builder.to_spec()
                        content = asdict(spec) if is_dataclass(spec) else str(spec)
                    case _:
                        raise errors.InvalidInputError(
                            f"Unsupported output_format {output_format!r}. "
                            "Supported values include: xml, model, spec"
                        )
            except errors.KsefMcpError:
                raise
            except Exception as exc:
                raise errors.DraftRuntimeError(
                    f"Failed to build draft: {exc}"
                ) from exc

            return BuildDraftResult(
                draft_id=session.draft_id,
                draft_type=session.draft_type,
                output_format=output_format,
                content=content,
            )

    def delete_draft(self, draft_id: UUID) -> DeleteDraftResult:
        with self._uow_factory() as uow:
            deleted = uow.draft_sessions.delete(draft_id)
            return DeleteDraftResult(draft_id=draft_id, deleted=deleted)

    def _spawn(
        self,
        session: DraftSession,
        *,
        context_id: str,
        method_name: str,
        new_context_id: str,
        args: dict[str, Any] | None,
    ) -> None:
        context = self._get_context_or_raise(session, context_id)
        if new_context_id in session.contexts:
            raise errors.InvalidInputError(
                f"Context {new_context_id!r} already exists."
            )

        bound_method = self._get_method_or_raise(context.builder, method_name)
        if self._classify_method(bound_method) is not DraftOperationType.SPAWN:
            raise errors.InvalidInputError(
                f"Method {method_name!r} on context {context_id!r} is not "
                "spawn-capable."
            )

        method_args = self._validate_args(bound_method, args)
        try:
            result = bound_method(**method_args)
        except ValidationError as exc:
            raise errors.InvalidInputError(str(exc)) from exc
        except Exception as exc:
            raise errors.DraftRuntimeError(
                f"Failed to spawn method {method_name!r}: {exc}"
            ) from exc

        if not self._is_builder_like(result):
            raise errors.InvalidInputError(
                f"Method {method_name!r} did not open a sub-builder."
            )

        session.contexts[new_context_id] = DraftContext(
            context_id=new_context_id,
            builder=result,
            parent_context_id=context_id,
            opened_via_method=method_name,
        )

    def _call(
        self,
        session: DraftSession,
        *,
        context_id: str,
        method_name: str,
        args: dict[str, Any] | None,
    ) -> None:
        context = self._get_context_or_raise(session, context_id)
        bound_method = self._get_method_or_raise(context.builder, method_name)

        if self._classify_method(bound_method) is not DraftOperationType.CALL:
            raise errors.InvalidInputError(
                f"Method {method_name!r} on context {context_id!r} is not "
                "call-capable."
            )

        method_args = self._validate_args(bound_method, args)
        try:
            result = bound_method(**method_args)
        except ValidationError as exc:
            raise errors.InvalidInputError(str(exc)) from exc
        except Exception as exc:
            raise errors.DraftRuntimeError(
                f"Failed to call method {method_name!r}: {exc}"
            ) from exc

        if self._is_builder_like(result) and result is not context.builder:
            raise errors.InvalidInputError(
                f"Method {method_name!r} opened a sub-builder. "
                "Use a spawn operation instead."
            )

    def _done(
        self,
        session: DraftSession,
        *,
        context_id: str,
        method_name: str,
    ) -> None:
        def remove_context_tree(
            removed_session: DraftSession,
            removed_context_id: str,
        ) -> None:
            child_ids = [
                child_id
                for child_id, child in removed_session.contexts.items()
                if child.parent_context_id == removed_context_id
            ]
            for child_id in child_ids:
                remove_context_tree(removed_session, child_id)

            try:
                removed_session.contexts.pop(removed_context_id)
            except KeyError as exc:
                raise errors.ResourceNotFoundError(
                    f"Context {removed_context_id!r} not found."
                ) from exc

        if method_name != "done":
            raise errors.InvalidInputError(
                f"done operations must call the 'done' method, got {method_name!r}."
            )

        context = self._get_context_or_raise(session, context_id)
        if context.parent_context_id is None:
            raise errors.InvalidInputError(
                "The root context cannot be closed with done."
            )

        bound_method = self._get_method_or_raise(context.builder, method_name)
        try:
            bound_method()
        except ValidationError as exc:
            raise errors.InvalidInputError(str(exc)) from exc
        except Exception as exc:
            raise errors.DraftRuntimeError(
                f"Failed to close context {context_id!r}: {exc}"
            ) from exc

        remove_context_tree(session, context_id)

    @staticmethod
    def _iter_method_names(builder: object) -> list[str]:
        method_names: list[str] = []
        for method_name in dir(builder):
            if method_name.startswith("_"):
                continue
            if method_name in _EXCLUDED_METHODS or method_name.endswith("_model"):
                continue

            candidate = getattr(builder, method_name)
            if callable(candidate):
                method_names.append(method_name)

        return method_names

    @staticmethod
    def _classify_method(bound_method: Callable[..., Any]) -> DraftOperationType:
        if getattr(bound_method, "__name__", "") == "done":
            return DraftOperationType.DONE

        return_hint = DraftRuntimeService._get_return_hint(bound_method)
        if return_hint is not None and "Builder" in str(return_hint): # [TODO] this is insanely brittle
            return DraftOperationType.SPAWN

        return DraftOperationType.CALL

    @staticmethod
    def _get_session_or_raise(
        uow: AbstractUnitOfWork,
        draft_id: UUID,
    ) -> DraftSession:
        try:
            return uow.draft_sessions.get_or_raise(draft_id)
        except ValueError as exc:
            raise errors.ResourceNotFoundError(
                f"Draft {draft_id!r} not found."
            ) from exc

    @staticmethod
    def _get_context_or_raise(
        session: DraftSession,
        context_id: str,
    ) -> DraftContext:
        context = session.contexts.get(context_id)
        if context is None:
            raise errors.ResourceNotFoundError(
                f"Context {context_id!r} not found."
            )
        return context

    @staticmethod
    def _validate_args(
        bound_method: Callable[..., Any],
        args: dict[str, Any] | None,
    ) -> dict[str, Any]:
        payload_model = get_method_payload_model(
            bound_method,
            include_extras=True,
            forbid_extra_fields=True,
        )
        try:
            parsed = payload_model.model_validate(args or {})
        except ValidationError as exc:
            raise errors.InvalidInputError(str(exc)) from exc

        return {
            field_name: getattr(parsed, field_name)
            for field_name in payload_model.model_fields
            if field_name in parsed.model_fields_set
            or getattr(parsed, field_name) is not None
        }

    @staticmethod
    def _is_builder_like(value: object) -> bool:
        return (
            value is not None
            and hasattr(value, "done")
            and callable(getattr(value, "done"))
            and not isinstance(value, FA3InvoiceBuilder)
        )

    @staticmethod
    def _get_method_or_raise(builder: object, method_name: str) -> Any:
        if not hasattr(builder, method_name):
            raise errors.ResourceNotFoundError(
                f"Method {method_name!r} is not available on this context."
            )

        bound_method = getattr(builder, method_name)
        if not callable(bound_method):
            raise errors.InvalidInputError(
                f"Attribute {method_name!r} is not callable on this context."
            )
        if method_name in _EXCLUDED_METHODS or method_name.endswith("_model"):
            raise errors.InvalidInputError(
                f"Method {method_name!r} is not exposed by the MCP draft runtime."
            )
        return bound_method

    @staticmethod
    def _get_type_hints(
        bound_method: Callable[..., Any],
        *,
        include_extras: bool,
    ) -> dict[str, Any]:
        try:
            return get_type_hints(
                inspect.unwrap(bound_method),
                include_extras=include_extras,
            )
        except Exception:
            return {}

    @staticmethod
    def _get_return_hint(bound_method: Callable[..., Any]) -> Any:
        return DraftRuntimeService._get_type_hints(
            bound_method,
            include_extras=False,
        ).get("return")

    @staticmethod
    def _serialize_contexts(session: DraftSession) -> list[DraftContextResult]:
        contexts = [
            DraftContextResult(
                context_id=context.context_id,
                builder_type=context.builder_type,
                parent_context_id=context.parent_context_id,
                opened_via_method=context.opened_via_method,
            )
            for context in session.contexts.values()
        ]
        contexts.sort(key=lambda item: (item.parent_context_id or "", item.context_id))
        return contexts


@lru_cache(maxsize=1)
def get_draft_runtime_service() -> DraftRuntimeService:
    return DraftRuntimeService()
