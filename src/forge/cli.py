from __future__ import annotations

from pathlib import Path

from .agent import AgentLoop
from .model_client import GroqClient
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolDefinition, ToolRegistry
from .tools.filesystem import list_files, read_file


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="list_files",
            description="List files and directories in a given path.",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=list_files,
        )
    )
    registry.register(
        ToolDefinition(
            name="read_file",
            description="Read the contents of a file from the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=read_file,
        )
    )
    return registry


def main() -> None:
    task = input("forge> ")
    workspace = Path.cwd().resolve()
    registry = build_registry()
    dispatcher = ToolDispatcher(registry)
    model_client = GroqClient(api_key=None, model="llama-3.1-8b-instant")
    loop = AgentLoop(
        model_client=model_client,
        tool_registry=registry,
        tool_dispatcher=dispatcher,
        max_steps=8,
        max_tool_calls=10,
    )

    result = loop.run(task)
    print("\n=== Forge result ===")
    print(result.final_answer or "No final answer was produced.")
    if result.last_error:
        print(f"Last error: {result.last_error}")
    print(f"Workspace: {workspace}")


if __name__ == "__main__":
    main()
