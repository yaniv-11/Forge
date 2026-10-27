from forge.agent import AgentLoop
from forge.model_client import GroqClient
from forge.tool_dispatcher import ToolDispatcher
from forge.tool_registry import ToolDefinition, ToolRegistry


def test_agent_loop_handles_final_answer_and_stops():
    registry = ToolRegistry()

    def list_files(path: str = ".") -> list[str]:
        return ["alpha.py", "beta.py"]

    registry.register(
        ToolDefinition(
            name="list_files",
            description="List files",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=list_files,
        )
    )

    class FakeModelClient:
        def send_messages(self, messages, tools):
            return {"final_answer": "Task complete"}

    loop = AgentLoop(
        model_client=FakeModelClient(),
        tool_registry=registry,
        tool_dispatcher=ToolDispatcher(registry),
        max_steps=3,
        max_tool_calls=5,
    )

    result = loop.run("List the files")
    assert result.final_answer == "Task complete"
    assert result.steps == 1


def test_agent_loop_enforces_max_tool_calls():
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

    class FakeModelClient:
        def send_messages(self, messages, tools):
            return {"tool_call": {"name": "echo", "arguments": {"value": "test"}}}

    loop = AgentLoop(
        model_client=FakeModelClient(),
        tool_registry=registry,
        tool_dispatcher=ToolDispatcher(registry),
        max_steps=10,
        max_tool_calls=1,
    )

    result = loop.run("Run echo once")
    assert result.last_error == "Max tool call budget exceeded."
    assert result.tool_calls == 1
