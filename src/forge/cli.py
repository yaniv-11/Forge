from __future__ import annotations

from pathlib import Path

from .agent import AgentLoop
from .config import Settings
from .model_client import OpenRouterClient
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolDefinition, ToolRegistry
from .tools.filesystem import list_files, read_file


def build_registry(workspace_root: Path) -> ToolRegistry:
    registry = ToolRegistry()

    def guarded_list_files(path: str = ".") -> list[str]:
        return list_files(path=path, workspace_root=workspace_root)

    def guarded_read_file(path: str) -> str:
        return read_file(path=path, workspace_root=workspace_root)

    registry.register(
        ToolDefinition(
            name="list_files",
            description="List files and directories in a given path within the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=guarded_list_files,
        )
    )
    registry.register(
        ToolDefinition(
            name="read_file",
            description="Read the contents of a file from within the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=guarded_read_file,
        )
    )
    return registry


def main() -> None:
    task = input("forge> ")
    workspace = Path.cwd().resolve()
    settings = Settings(
        workspace_root=workspace,
        provider="openrouter",
        model_name="openai/gpt-4o-mini",
    )
    registry = build_registry(workspace)
    dispatcher = ToolDispatcher(registry)
    model_client = OpenRouterClient(
        api_key=settings.api_key,
        model=settings.model_name,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        site_url=settings.site_url,
        app_name=settings.app_name,
    )
    loop = AgentLoop(
        model_client=model_client,
        tool_registry=registry,
        tool_dispatcher=dispatcher,
        max_steps=settings.max_steps,
        max_tool_calls=settings.max_tool_calls,
        debug=settings.debug,
    )

    result = loop.run(task)
    print("\n=== Forge result ===")
    print(result.final_answer or "No final answer was produced.")
    if result.last_error:
        print(f"Last error: {result.last_error}")
    print(f"Workspace: {workspace}")


if __name__ == "__main__":
    main()
