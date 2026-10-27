from forge.tool_registry import ToolDefinition, ToolRegistry


def test_tool_registry_registers_and_lists_tools():
    registry = ToolRegistry()

    def sample_tool(path: str) -> str:
        return path

    registry.register(
        ToolDefinition(
            name="sample_tool",
            description="Example tool",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=sample_tool,
        )
    )

    assert registry.get("sample_tool").name == "sample_tool"
    assert len(registry.list_tools()) == 1
    assert registry.model_tools()[0]["function"]["name"] == "sample_tool"


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()

    def sample_tool(path: str) -> str:
        return path

    registry.register(
        ToolDefinition(
            name="dup",
            description="Example tool",
            arguments_schema={"type": "object", "properties": {}},
            handler=sample_tool,
        )
    )

    try:
        registry.register(
            ToolDefinition(
                name="dup",
                description="Dup",
                arguments_schema={"type": "object", "properties": {}},
                handler=sample_tool,
            )
        )
        assert False, "Expected duplicate registration to fail"
    except ValueError:
        pass
