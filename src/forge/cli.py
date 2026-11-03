from __future__ import annotations

from pathlib import Path
import argparse

from .agent import AgentLoop
from .config import Settings
from .git_tools import GitCheckpointManager
from .model_client import OpenRouterClient
from .planning import PlanManager
from .persistence import SessionStore
from .tool_dispatcher import ToolDispatcher
from .tools.registry import build_registry
from .observability import RunRecorder
from .memory import ForgeDatabase, RepositoryIndex, WorkspaceMemory, compact_messages


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
        memory_context_provider=lambda task: "\n\n".join(
            part for part in (
                workspace_memory.prompt_context(),
                repository_index.prompt_context(task),
                database.memory_prompt_context(),
            ) if part
        ),
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

    def execute(task_text: str, stored_task: str | None = None) -> None:
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
            "modified_files": result.modified_files,
            "commands": result.commands,
            "side_effects": result.side_effects,
        }
        if active_session:
            saved = store.update_session(active_session, result_state)
            session_id = active_session
        else:
            session_id = store.create_session(task_text, result_state)
            active_session = session_id
        previous_messages = result.messages
        session_summary = str(result_state["summary"])
        database.save_session(
            session_id,
            stored_task or task_text,
            result_state["summary"],
            result.messages,
            make_plan_data(result),
            result.usage,
        )
        database.add_episode(
            session_id,
            stored_task or task_text,
            "completed" if not result.last_error else "completed_with_errors",
            result.final_answer or "",
            result.modified_files,
            result.commands,
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
        plan_state = saved_state.get("plan") or {}
        loop.plan_manager = PlanManager(session["task"])
        loop.plan_manager.plan.objective = session["task"]
        for step in plan_state.get("steps", []):
            loop.plan_manager.add_step(
                str(step.get("name", "continue task")),
                str(step.get("verification", "")),
                [str(value) for value in step.get("depends_on", [])],
            )
            restored = loop.plan_manager.plan.steps[-1]
            restored.status = str(step.get("status", "pending"))
            restored.notes = str(step.get("notes", ""))
        pending_steps = [
            step["name"] for step in loop.plan_manager.plan.steps
            if step.status != "done"
        ]
        continuation = session["task"]
        if pending_steps:
            continuation = (
                f"Continue the original task: {session['task']}\n"
                "Resume from these pending plan steps:\n- "
                + "\n- ".join(pending_steps)
            )
        execute(continuation, stored_task=session["task"])
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
