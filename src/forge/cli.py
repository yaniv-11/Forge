from __future__ import annotations

from pathlib import Path

from .agent import AgentLoop
from .config import Settings
from .git_tools import GitCheckpointManager
from .model_client import OpenRouterClient
from .persistence import SessionStore
from .planning import PlanManager
from .repo_inspector import RepositoryInspector
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolDefinition, ToolRegistry
from .tools.filesystem import create_file, edit_file, list_files, read_file, replace_file, run_command, search_files


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

    def guarded_create_file(path: str, content: str) -> str:
        return create_file(path=path, content=content, workspace_root=workspace_root)

    def guarded_replace_file(path: str, content: str) -> str:
        return replace_file(path=path, content=content, workspace_root=workspace_root)

    def guarded_edit_file(path: str, old: str, new: str) -> str:
        return edit_file(path=path, old=old, new=new, workspace_root=workspace_root)

    def guarded_run_command(command: list[str] | str, cwd: str = ".", timeout: int = 30) -> dict[str, object]:
        return run_command(
            command=command,
            cwd=cwd,
            workspace_root=workspace_root,
            timeout=timeout,
        )

    def guarded_create_plan(task: str) -> dict[str, object]:
        manager = PlanManager(task)
        manager.add_step("inspect repository")
        manager.add_step("apply targeted fix")
        manager.add_step("verify with tests")
        return manager.to_dict()

    def guarded_inspect_repo(task: str, max_files: int = 10) -> dict[str, object]:
        return RepositoryInspector(workspace_root).inspect(task, max_files=max_files)

    def guarded_create_checkpoint(message: str) -> dict[str, object]:
        return GitCheckpointManager(workspace_root).create_checkpoint(message)

    def guarded_resume_session(session_id: str) -> dict[str, object]:
        return SessionStore(workspace_root / ".forge_sessions").resume_session(session_id)

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
            permission="read",
            risk="low",
        )
    )
    registry.register(
        ToolDefinition(
            name="inspect_repo",
            description="Score repository files by relevance to the user task and return the most likely files to inspect first.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "max_files": {"type": "integer"},
                },
                "required": ["task"],
            },
            handler=guarded_inspect_repo,
            permission="read",
            risk="low",
        )
    )
    registry.register(
        ToolDefinition(
            name="plan_task",
            description="Create a lightweight execution plan with explicit steps and a bounded repair budget.",
            arguments_schema={
                "type": "object",
                "properties": {"task": {"type": "string"}},
                "required": ["task"],
            },
            handler=guarded_create_plan,
            permission="read",
            risk="low",
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
            permission="read",
            risk="low",
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
            name="run_command",
            description="Run an executable in the workspace with a constrained working directory and output capture.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "command": {"type": ["array", "string"]},
                    "cwd": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
            handler=guarded_run_command,
            permission="command",
            risk="medium",
            approval_required=True,
        )
    )
    registry.register(
        ToolDefinition(
            name="create_checkpoint",
            description="Create a conservative Git checkpoint for the current workspace before risky edits or recovery actions.",
            arguments_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            handler=guarded_create_checkpoint,
            permission="write",
            risk="medium",
            approval_required=True,
        )
    )
    registry.register(
        ToolDefinition(
            name="resume_session",
            description="Resume a persisted session only when no destructive side effects are recorded for that session.",
            arguments_schema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
            handler=guarded_resume_session,
            permission="read",
            risk="low",
        )
    )
    registry.register(
        ToolDefinition(
            name="create_file",
            description="Create a new file inside the workspace. Fails if the file already exists.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=guarded_create_file,
            permission="write",
            risk="low",
        )
    )
    registry.register(
        ToolDefinition(
            name="replace_file",
            description="Overwrite an existing file inside the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=guarded_replace_file,
            permission="write",
            risk="low",
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
            permission="write",
            risk="low",
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
