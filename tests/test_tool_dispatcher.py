from forge.tool_dispatcher import ToolDispatcher
from forge.tool_registry import ToolDefinition, ToolRegistry


def test_tool_dispatcher_executes_registered_tool():
    registry = ToolRegistry()

    def echo(value: str) -> str:
        return value

    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo tool",
            arguments_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=echo,
        )
    )

    dispatcher = ToolDispatcher(registry)
    result = dispatcher.execute({"name": "echo", "arguments": {"value": "hello"}})

    assert result["status"] == "ok"
    assert result["result"] == "hello"


def test_tool_dispatcher_reports_unknown_tool_and_invalid_arguments():
    registry = ToolRegistry()
    dispatcher = ToolDispatcher(registry)

    missing = dispatcher.execute({"name": "missing", "arguments": {}})
    assert missing["status"] == "error"
    assert "Unknown tool" in missing["error"]

    def echo(value: str) -> str:
        return value

    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo tool",
            arguments_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=echo,
        )
    )

    bad_args = dispatcher.execute({"name": "echo", "arguments": {"wrong": "value"}})
    assert bad_args["status"] == "error"
    assert "Invalid arguments" in bad_args["error"]
