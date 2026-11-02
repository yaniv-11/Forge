from __future__ import annotations

from pathlib import Path
import argparse

from .agent import AgentLoop
from .config import Settings
from .git_tools import GitCheckpointManager
from .model_client import OpenRouterClient
from .persistence import SessionStore
from .planning import PlanManager
from .repo_inspector import RepositoryInspector
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolDefinition, ToolRegistry
from .observability import RunRecorder
from .memory import ForgeDatabase, RepositoryIndex, WorkspaceMemory, compact_messages
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

    def guarded_git_status() -> dict[str, object]:
        return GitCheckpointManager(workspace_root).status()

    def guarded_git_diff(paths: list[str] | None = None, staged: bool = False) -> dict[str, object]:
        return GitCheckpointManager(workspace_root).diff(paths=paths, staged=staged)

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
            name="git_status",
            description="Show the concise Git status and branch information for the workspace.",
            arguments_schema={"type": "object", "properties": {}, "required": []},
            handler=guarded_git_status,
            permission="read",
            risk="low",
        )
    )
    registry.register(
        ToolDefinition(
            name="git_diff",
            description="Show unstaged or staged Git changes for the workspace.",
            arguments_schema={
                "type": "object",
                "properties": {
                    "paths": {"type": "array"},
                    "staged": {"type": "boolean"},
                },
                "required": [],
            },
            handler=guarded_git_diff,
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


def _approval_prompt(tool_name: str, arguments: dict[str, object]) -> bool:
    print(f"\nApproval requested for {tool_name}:")
    print(arguments)
    while True:
        answer = input("Approve this tool call? [y/N/a=approve all] ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer == "a":
            return True
        if answer in {"n", "no", ""}:
            return False


def _show_progress(event: str, data: dict[str, object]) -> None:
    if event == "tool_retry":
        print(f"[retry] {data.get('name')} attempt {data.get('attempt')}: {data.get('reason')}")
    elif event == "tool_result":
        print(f"[tool] {data.get('name')}: {data.get('status')}")
    elif event == "task_completed":
        print(f"[done] completed in {float(data.get('elapsed_seconds', 0)):.2f}s")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="forge", description="Run the Forge coding agent")
    parser.add_argument("task", nargs="*", help="One-shot task text")
    parser.add_argument("-w", "--workspace", default=".", help="Workspace directory")
    parser.add_argument("--resume", help="Resume a persisted session ID")
    parser.add_argument("--no-parallel-tools", action="store_true", help="Disable parallel tool execution")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    if not workspace.exists():
        parser.error(f"Workspace does not exist: {workspace}")
    settings = Settings(
        workspace_root=workspace,
        provider="openrouter",
        model_name="openai/gpt-4o-mini",
    )
    registry = build_registry(workspace)
    dispatcher = ToolDispatcher(registry, approval_handler=_approval_prompt)
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
        parallel_tools=not args.no_parallel_tools,
        observability=RunRecorder(workspace),
        event_callback=_show_progress,
    )
    store = SessionStore(workspace / ".forge_sessions")
    workspace_memory = WorkspaceMemory(workspace)
    database = ForgeDatabase(workspace)
    repository_index = RepositoryIndex(workspace)
    repository_index.rebuild()
    history: list[str] = []
    active_session: str | None = args.resume
    previous_messages: list[dict[str, object]] = []
    session_summary = ""

    def summarize_messages(messages: list[dict[str, object]]) -> str:
        user_tasks = [
            str(message.get("content", ""))[:500]
            for message in messages
            if message.get("role") == "user"
        ]
        tool_results = sum(message.get("role") == "tool" for message in messages)
        return (
            f"Tasks: {' | '.join(user_tasks[-3:])}. "
            f"{tool_results} tool result(s) recorded in this session."
        )

    def make_plan_data(result: object) -> dict[str, object]:
        plan = getattr(result, "plan", {}) or {}
        if plan:
            return plan
        return loop.plan_manager.to_dict()

    def execute(task_text: str) -> None:
        nonlocal active_session, previous_messages, session_summary
        initial_messages = []
        if previous_messages:
            initial_messages.append({
                "role": "system",
                "content": f"Previous session summary: {session_summary}",
            })
            initial_messages.extend(previous_messages[-12:])
        loop.initial_messages = initial_messages
        result = loop.run(task_text)
        result_state = {
            "messages": result.messages,
            "summary": summarize_messages(result.messages),
            "usage": result.usage,
            "elapsed_seconds": result.elapsed_seconds,
            "tool_retries": result.tool_retries,
            "plan": make_plan_data(result),
            "side_effects": [],
        }
        if active_session:
            saved = store.update_session(active_session, result_state)
            session_id = active_session
        else:
            session_id = store.create_session(task_text, result_state)
            active_session = session_id
        database.save_session(
            session_id,
            task_text,
            result_state["summary"],
            result.messages,
            make_plan_data(result),
            result.usage,
        )
        previous_messages = result.messages
        session_summary = str(result_state["summary"])
        database.add_episode(
            session_id,
            task_text,
            "completed" if not result.last_error else "completed_with_errors",
            result.final_answer or "",
        )
        history.append(task_text)
        print("\n=== Forge result ===")
        print(result.final_answer or "No final answer was produced.")
        if result.last_error:
            print(f"Last error: {result.last_error}")
        print(f"Tokens: {result.usage.get('total_tokens', 0)} | Time: {result.elapsed_seconds:.2f}s | Session: {session_id}")
        print(f"Workspace: {workspace}")

    if args.resume:
        session = store.resume_session(args.resume)
        print(f"Resumed session {args.resume}: {session['task']}")
        saved_state = session.get("state", {})
        previous_messages = saved_state.get("messages", [])[-12:]
        session_summary = saved_state.get("summary", "")
        print(f"Summary: {session_summary or 'No prior summary stored.'}")
        execute(session["task"])
        return

    if args.task:
        execute(" ".join(args.task))
        return

    print(f"Forge workspace: {workspace}")
    print("Commands: /help, /status, /sessions, /history, /exit")
    while True:
        try:
            task = input("forge> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not task:
            continue
        if task in {"/exit", "/quit"}:
            return
        if task == "/help":
            print("Enter a coding task, or use /status, /sessions, /history, /exit.")
            continue
        if task == "/status":
            print(GitCheckpointManager(workspace).status()["output"])
            continue
        if task == "/sessions":
            print("\n".join(store.list_sessions()) or "No sessions.")
            continue
        if task == "/history":
            print("\n".join(f"{index + 1}. {item}" for index, item in enumerate(history)) or "No task history.")
            continue
        execute(task)


if __name__ == "__main__":
    main()
