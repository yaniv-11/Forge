from __future__ import annotations

from typing import Any

from .tool_registry import ToolRegistry


def _matches_type(expected_type: Any, value: Any) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(option, value) for option in expected_type)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "null":
        return value is None
    return True


class ToolDispatcher:
    """Validates and invokes registry-defined tools."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def validate_arguments(self, schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
        if not isinstance(schema, dict):
            return None

        required_fields = schema.get("required", [])
        for field_name in required_fields:
            if field_name not in arguments:
                return f"Missing required argument: {field_name}"

        for field_name, field_spec in (schema.get("properties") or {}).items():
            if field_name not in arguments:
                continue
            expected_type = field_spec.get("type") if isinstance(field_spec, dict) else None
            if expected_type and not _matches_type(expected_type, arguments[field_name]):
                return f"Argument '{field_name}' must match type {expected_type}"

        return None

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        if not isinstance(name, str):
            return {"status": "error", "error_type": "validation_error", "error": "Tool call name is invalid."}

        try:
            tool = self.registry.get(name)
        except KeyError:
            return {"status": "error", "error_type": "tool_not_found", "error": f"Unknown tool: {name}"}

        if not isinstance(arguments, dict):
            return {"status": "error", "error_type": "validation_error", "error": "Tool arguments must be an object."}

        validation_error = self.validate_arguments(tool.arguments_schema, arguments)
        if validation_error:
            return {"status": "error", "error_type": "validation_error", "error": validation_error}

        if tool.approval_required:
            return {"status": "error", "error_type": "permission_denied", "error": f"Tool {name} requires user approval."}

        try:
            result = tool.handler(**arguments)
            return {"status": "ok", "name": name, "result": result, "permission": tool.permission, "risk": tool.risk}
        except TypeError as exc:
            return {"status": "error", "error_type": "validation_error", "error": f"Invalid arguments for tool {name}: {exc}"}
        except Exception as exc:  # pragma: no cover - defensive guard
            return {"status": "error", "error_type": "execution_error", "error": f"Tool execution failed for {name}: {exc}"}
