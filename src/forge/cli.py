from __future__ import annotations

from pathlib import Path

from .agent import AgentLoop
from .config import Settings
from .model_client import OpenRouterClient
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolDefinition, ToolRegistry
from .tools.filesystem import edit_file, list_files, read_file, search_files, write_file


def build_registry(workspace_root: Path) -> ToolRegistry:
    registry = ToolRegistry()

    def guarded_list_files(path: str = ".") -> list[str]:
        return list_files(path=path, workspace_root=workspace_root)

    def guarded_read_file(path: str) -> str:
        return read_file(path=path, workspace_root=workspace_root)

    def guarded_search_files(pattern: str, path: str = ".", max_results: int = 20) -> list[str]:
        return search_files(
            pattern=pattern,
            path=path,
            workspace_root=workspace_root,
            max_results=max_results,
        )

    def guarded_write_file(path: str, content: str) -> str:
        return write_file(path=path, content=content, workspace_root=workspace_root)

    def guarded_edit_file(path: str, old: str, new: str) -> str:
        return edit_file(path=path, old=old, new=new, workspace_root=workspace_root)

    registry.register(
        ToolDefinition(
            name="list_files",
            description="List child paths within a directory inside the workspace. Use this for safe discovery before reading files.",
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
            name="search_files",
            description="Search for text within files in the workspace and return matching file paths with line numbers.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "max_results": {"type": "integer", "default": 20},
                },
                "required": ["pattern"],
            },
            handler=guarded_search_files,
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
    registry.register(
        ToolDefinition(
            name="write_file",
            description="Create a new file or overwrite an existing file inside the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=guarded_write_file,
        )
    )
    registry.register(
        ToolDefinition(
            name="edit_file",
            description="Replace a specific snippet in an existing file inside the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            },
            handler=guarded_edit_file,
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
