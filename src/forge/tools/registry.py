from __future__ import annotations

from pathlib import Path
from typing import Any

from ..git_tools import GitCheckpointManager
from ..persistence import SessionStore
from ..planning import PlanManager
from ..repo_inspector import RepositoryInspector
from ..memory import ForgeDatabase
from ..tool_registry import ToolRegistry, forge_tool
from .filesystem import (
    create_file as create_workspace_file,
    edit_file as edit_workspace_file,
    list_files as list_workspace_files,
    read_file as read_workspace_file,
    replace_file as replace_workspace_file,
    run_command as run_workspace_command,
    search_files as search_workspace_files,
)


@forge_tool(
    name="list_files",
    description="List child paths within a directory inside the workspace. Use this for safe discovery before reading files.",
    arguments_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
def list_files(path: str = ".", workspace_root: Path | None = None) -> list[str]:
    return list_workspace_files(path=path, workspace_root=workspace_root)


@forge_tool(
    name="read_file",
    description="Read the contents of a file from within the workspace.",
    arguments_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
def read_file(path: str, workspace_root: Path | None = None) -> str:
    return read_workspace_file(path=path, workspace_root=workspace_root)


@forge_tool(
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
)
def search_files(
    pattern: str,
    path: str = ".",
    max_results: int = 20,
    workspace_root: Path | None = None,
) -> list[str]:
    return search_workspace_files(
        pattern=pattern,
        path=path,
        workspace_root=workspace_root,
        max_results=max_results,
    )


@forge_tool(
    name="create_file",
    description="Create a new file inside the workspace. Fails if the file already exists.",
    arguments_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    },
    permission="write",
)
def create_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    return create_workspace_file(path=path, content=content, workspace_root=workspace_root)


@forge_tool(
    name="replace_file",
    description="Overwrite an existing file inside the workspace.",
    arguments_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        "required": ["path", "content"],
    },
    permission="write",
)
def replace_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    return replace_workspace_file(path=path, content=content, workspace_root=workspace_root)


@forge_tool(
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
    permission="write",
)
def edit_file(path: str, old: str, new: str, workspace_root: Path | None = None) -> str:
    return edit_workspace_file(path=path, old=old, new=new, workspace_root=workspace_root)


@forge_tool(
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
    permission="command",
    risk="medium",
    approval_required=True,
)
def run_command(
    command: list[str] | str,
    cwd: str = ".",
    timeout: int = 30,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    return run_workspace_command(
        command=command,
        cwd=cwd,
        workspace_root=workspace_root,
        timeout=timeout,
    )


@forge_tool(
    name="git_status",
    description="Show the concise Git status and branch information for the workspace.",
    arguments_schema={"type": "object", "properties": {}, "required": []},
)
def git_status(workspace_root: Path) -> dict[str, Any]:
    return GitCheckpointManager(workspace_root).status()


@forge_tool(
    name="git_diff",
    description="Show unstaged or staged Git changes for the workspace.",
    arguments_schema={
        "type": "object",
        "properties": {"paths": {"type": "array"}, "staged": {"type": "boolean"}},
        "required": [],
    },
)
def git_diff(
    paths: list[str] | None = None,
    staged: bool = False,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    return GitCheckpointManager(workspace_root).diff(paths=paths, staged=staged)


@forge_tool(
    name="inspect_repo",
    description="Score repository files by relevance to the user task and return the most likely files to inspect first.",
    arguments_schema={
        "type": "object",
        "properties": {"task": {"type": "string"}, "max_files": {"type": "integer"}},
        "required": ["task"],
    },
)
def inspect_repo(task: str, max_files: int = 10, workspace_root: Path | None = None) -> dict[str, Any]:
    return RepositoryInspector(workspace_root).inspect(task, max_files=max_files)


@forge_tool(
    name="plan_task",
    description="Create or replace the execution plan with task-specific steps, dependencies, and verification.",
    arguments_schema={
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "verification": {"type": "string"},
                        "depends_on": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["name"],
                },
            },
        },
        "required": ["task"],
    },
)
def plan_task(task: str, steps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manager = PlanManager(task)
    if steps:
        manager.replace_plan(steps)
    else:
        manager.add_step("inspect repository", "Relevant files are identified.")
        manager.add_step("apply targeted fix", "The requested files are updated.", ["inspect repository"])
        manager.add_step("verify with tests", "Relevant tests pass.", ["apply targeted fix"])
    return manager.to_dict()


@forge_tool(
    name="remember_workspace",
    description="Store durable workspace knowledge for use in future tasks.",
    arguments_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["key", "value"],
    },
)
def remember_workspace(
    key: str,
    value: str,
    category: str = "fact",
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    return ForgeDatabase(workspace_root).remember(key, value, category)


@forge_tool(
    name="create_checkpoint",
    description="Create a conservative Git checkpoint for the current workspace before risky edits or recovery actions.",
    arguments_schema={
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
    permission="write",
    risk="medium",
    approval_required=True,
)
def create_checkpoint(message: str, workspace_root: Path | None = None) -> dict[str, Any]:
    return GitCheckpointManager(workspace_root).create_checkpoint(message)


@forge_tool(
    name="resume_session",
    description="Resume a persisted session only when no destructive side effects are recorded for that session.",
    arguments_schema={
        "type": "object",
        "properties": {"session_id": {"type": "string"}},
        "required": ["session_id"],
    },
)
def resume_session(session_id: str, workspace_root: Path | None = None) -> dict[str, Any]:
    return SessionStore(workspace_root / ".forge_sessions").resume_session(session_id)


TOOLS = (
    list_files,
    read_file,
    search_files,
    create_file,
    replace_file,
    edit_file,
    run_command,
    git_status,
    git_diff,
    inspect_repo,
    plan_task,
    remember_workspace,
    create_checkpoint,
    resume_session,
)


def build_registry(workspace_root: Path) -> ToolRegistry:
    registry = ToolRegistry()
    for tool_handler in TOOLS:
        registry.register_decorated(tool_handler, workspace_root=workspace_root)
    return registry
