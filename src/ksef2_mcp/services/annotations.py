import inspect
from typing import Any, Callable, get_type_hints

from pydantic import BaseModel, ConfigDict, create_model


def get_method_payload_model(
    bound_method: Callable[..., Any],
    *,
    include_extras: bool,
    forbid_extra_fields: bool = True,
) -> type[BaseModel]:
    hints = get_type_hints(
        inspect.unwrap(bound_method),
        include_extras=include_extras,
    )
    signature = inspect.signature(bound_method)

    fields: dict[str, tuple[Any, Any]] = {}
    for name, parameter in signature.parameters.items():
        annotation = hints.get(name, Any)
        default = (
            ...
            if parameter.default is inspect.Signature.empty
            else parameter.default
        )
        fields[name] = (annotation, default)

    config = ConfigDict({"extra": "forbid" if forbid_extra_fields else "allow"})
    return create_model("MethodPayload", **fields, __config__=config)


def get_method_payload_json_schema(
    bound_method: Callable[..., Any],
    *,
    include_extras: bool,
    primitive_union_format: bool = True,
    forbid_extra_fields: bool = True,
    extra_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_model = get_method_payload_model(
        bound_method,
        include_extras=include_extras,
        forbid_extra_fields=forbid_extra_fields,
    )
    schema = payload_model.model_json_schema(
        union_format="primitive_type_array" if primitive_union_format else "any_of"
    )
    normalized_schema = _normalize_schema_tree(schema)

    return {**normalized_schema, **(extra_schema or {})}


def _normalize_schema_tree(schema: dict[str, Any]) -> dict[str, Any]:
    definitions = schema.get("$defs", {})

    normalized_schema = {
        key: _normalize_schema_value(value, definitions)
        for key, value in schema.items()
    }
    if "$defs" in normalized_schema:
        normalized_schema["$defs"] = {
            key: _normalize_schema_value(value, definitions)
            for key, value in definitions.items()
        }

    return normalized_schema


def _normalize_schema_value(
    value: Any,
    definitions: dict[str, Any],
) -> Any:
    if isinstance(value, dict):
        normalized = {
            key: _normalize_schema_value(item, definitions)
            for key, item in value.items()
        }
        normalized = _normalize_nullable_schema(normalized)
        normalized = _normalize_builder_format(normalized, definitions)
        return normalized

    if isinstance(value, list):
        return [_normalize_schema_value(item, definitions) for item in value]

    return value


def _normalize_nullable_schema(schema: dict[str, Any]) -> dict[str, Any]:
    type_value = schema.get("type")
    if (
        schema.get("x-builder-prefer-omit-when-null") is True
        and isinstance(type_value, list)
        and "null" in type_value
    ):
        remaining_types = [item for item in type_value if item != "null"]
        if len(remaining_types) == 1:
            schema["type"] = remaining_types[0]
        elif remaining_types:
            schema["type"] = remaining_types

    any_of = schema.get("anyOf")
    if (
        schema.get("x-builder-prefer-omit-when-null") is True
        and isinstance(any_of, list)
    ):
        non_null_options = [
            option
            for option in any_of
            if not _is_null_schema(option)
        ]
        if len(non_null_options) == 1:
            replacement = non_null_options[0]
            merged = {key: value for key, value in schema.items() if key != "anyOf"}
            merged.update(replacement)
            return merged

    return schema


def _normalize_builder_format(
    schema: dict[str, Any],
    definitions: dict[str, Any],
) -> dict[str, Any]:
    builder_format = schema.get("x-builder-format")
    if builder_format is None:
        return schema

    metadata = {key: value for key, value in schema.items() if key != "anyOf"}

    match builder_format:
        case "decimal-string":
            metadata.pop("$ref", None)
            metadata["type"] = "string"
            metadata["format"] = "decimal"
            return metadata
        case "date":
            metadata.pop("$ref", None)
            metadata["type"] = "string"
            metadata["format"] = "date"
            return metadata
        case "date-time":
            metadata.pop("$ref", None)
            metadata["type"] = "string"
            metadata["format"] = "date-time"
            return metadata
        case "country-code":
            metadata.pop("$ref", None)
            metadata["type"] = "string"
            metadata["format"] = "country-code"
            metadata["minLength"] = 2
            metadata["maxLength"] = 2
            return metadata
        case "enum-string":
            metadata.pop("$ref", None)
            metadata["type"] = "string"
            enum_values = _collect_enum_values(schema, definitions)
            if enum_values:
                metadata["enum"] = enum_values
            return metadata
        case "object":
            reference_option = _select_reference_option(schema, definitions)
            if reference_option is None:
                return metadata
            metadata.pop("type", None)
            metadata.pop("additionalProperties", None)
            metadata.update(reference_option)
            return metadata
        case _:
            return schema


def _select_reference_option(
    schema: dict[str, Any],
    definitions: dict[str, Any],
) -> dict[str, Any] | None:
    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return None

    for option in any_of:
        if "$ref" in option:
            ref_name = _ref_name(option["$ref"])
            if ref_name in definitions:
                return {"$ref": option["$ref"]}

    for option in any_of:
        if option.get("type") == "object":
            return option

    return None


def _collect_enum_values(
    schema: dict[str, Any],
    definitions: dict[str, Any],
) -> list[Any]:
    enum_values: list[Any] = []

    if "enum" in schema:
        return list(schema["enum"])

    if "$ref" in schema:
        resolved = definitions.get(_ref_name(schema["$ref"]))
        if isinstance(resolved, dict):
            return _collect_enum_values(resolved, definitions)
        return enum_values

    any_of = schema.get("anyOf")
    if not isinstance(any_of, list):
        return enum_values

    for option in any_of:
        for enum_value in _collect_enum_values(option, definitions):
            if enum_value not in enum_values:
                enum_values.append(enum_value)

    return enum_values


def _is_null_schema(schema: dict[str, Any]) -> bool:
    type_value = schema.get("type")
    if type_value == "null":
        return True
    if isinstance(type_value, list):
        return type_value == ["null"]
    return False


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]
