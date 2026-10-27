from __future__ import annotations

from typing import Any

from .tool_registry import ToolRegistry


class ToolDispatcher:
    """Validates and invokes registry-defined tools."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        if not isinstance(name, str):
            return {"status": "error", "error": "Tool call name is invalid."}

        try:
            tool = self.registry.get(name)
        except KeyError:
            return {"status": "error", "error": f"Unknown tool: {name}"}

        if not isinstance(arguments, dict):
            return {"status": "error", "error": "Tool arguments must be an object."}

        try:
            result = tool.handler(**arguments)
            return {"status": "ok", "name": name, "result": result}
        except TypeError as exc:
            return {"status": "error", "error": f"Invalid arguments for tool {name}: {exc}"}
        except Exception as exc:  # pragma: no cover - defensive guard
            return {"status": "error", "error": f"Tool execution failed for {name}: {exc}"}
