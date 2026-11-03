from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from inspect import signature
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

    def register_decorated(self, handler: Callable[..., Any], **context: Any) -> None:
        definition = getattr(handler, "__forge_tool__", None)
        if definition is None:
            raise ValueError(f"{handler.__name__!r} is not a registered tool handler.")

        bound_handler = handler
        context_parameters = {
            name: value
            for name, value in context.items()
            if name in signature(handler).parameters
        }
        if context_parameters:
            bound_handler = partial(handler, **context_parameters)

        self.register(ToolDefinition(
            name=definition.name,
            description=definition.description,
            arguments_schema=definition.arguments_schema,
            handler=bound_handler,
            permission=definition.permission,
            risk=definition.risk,
            approval_required=definition.approval_required,
        ))


def forge_tool(
    name: str,
    description: str,
    arguments_schema: dict[str, Any],
    permission: str = "read",
    risk: str = "low",
    approval_required: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Attach tool metadata to a callable."""

    def decorate(handler: Callable[..., Any]) -> Callable[..., Any]:
        definition = ToolDefinition(
            name=name,
            description=description,
            arguments_schema=arguments_schema,
            handler=handler,
            permission=permission,
            risk=risk,
            approval_required=approval_required,
        )
        setattr(handler, "__forge_tool__", definition)
        return handler

    return decorate
