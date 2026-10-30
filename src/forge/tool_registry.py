from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDefinition:
    """Typed metadata for a callable tool."""

    name: str
    description: str
    arguments_schema: dict[str, Any]
    handler: Callable[..., Any]
    permission: str = "read"
    risk: str = "low"
    approval_required: bool = False


class ToolRegistry:
    """Central tool registry used by the model and dispatcher."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def model_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.arguments_schema,
                },
            }
            for tool in self.list_tools()
        ]
