from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

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


def _use_color() -> bool:
    return (
        sys.stdout.isatty()
        and os.getenv("NO_COLOR") is None
        and os.getenv("TERM") != "dumb"
    )


if _use_color():
    C_RESET = "\033[0m"
    C_BOLD = "\033[1m"
    C_DIM = "\033[2m"
    C_CYAN = "\033[36m"
    C_GREEN = "\033[32m"
    C_YELLOW = "\033[33m"
    C_RED = "\033[31m"
else:
    C_RESET = C_BOLD = C_DIM = C_CYAN = C_GREEN = C_YELLOW = C_RED = ""


def _style(text: object, color: str) -> str:
    return f"{color}{text}{C_RESET}" if color else str(text)


def _print_box(title: str, body: object, color: str = C_CYAN, width: int = 88) -> None:
    lines = str(body).expandtabs(4).splitlines() or [""]
    print()
    print(_style(f" {title} ".center(width, "="), C_BOLD + color))
    for line in lines:
        print(line)
    print(_style("=" * width, color))


def _print_banner(workspace: Path) -> None:
    print()
    print(_style("  F O R G E", C_BOLD + C_CYAN))
    print(_style("  Workspace", C_DIM), workspace)
    print()
    print(_style("  Commands", C_BOLD), "/help  /status  /sessions  /history  /exit")
    print(_style("  " + "-" * 84, C_DIM))


def _print_workspace_preflight(workspace: Path) -> None:
    _print_section("Workspace")
    print(_style("  Path", C_BOLD), workspace)
    git = GitCheckpointManager(workspace)
    try:
        status = git.status()
    except (subprocess.CalledProcessError, OSError):
        print(_style("  Git", C_DIM), "not available")
        return
    output = status["output"].strip()
    print(_style("  Git", C_DIM), "repository" if output else "repository (clean)")
    if output:
        print(output)


def _print_section(title: str) -> None:
    print()
    print(_style(f" {title} ", C_BOLD + C_CYAN))
    print(_style("-" * (len(title) + 2), C_DIM))


def _approval_prompt(tool_name: str, arguments: dict[str, object]) -> bool:
    print()
    print(_style(f" Approval requested: {tool_name} ", C_BOLD + C_YELLOW))
    print(json.dumps(arguments, indent=2, ensure_ascii=False))
    while True:
        answer = input(_style("Approve this tool call? [y/N/a=approve all] ", C_BOLD)).strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer == "a":
            return True
        if answer in {"n", "no", ""}:
            return False


def _show_progress(event: str, data: dict[str, object]) -> None:
    if event == "tool_retry":
        print(_style("  ↻ retry", C_YELLOW), f"{data.get('name')} attempt {data.get('attempt')}  {C_DIM}{data.get('reason')}{C_RESET}")
    elif event == "tool_result":
        status = str(data.get("status"))
        marker = "✓" if status == "ok" else "✗"
        color = C_GREEN if status == "ok" else C_RED
        print(_style(f"  {marker} tool", color), data.get("name"))
    elif event == "task_completed":
        print(_style("  ✓ completed", C_GREEN), f"in {float(data.get('elapsed_seconds', 0)):.2f}s")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="forge", description="Run the Forge coding agent")
    parser.add_argument("task", nargs="*", help="One-shot task text")
    parser.add_argument("-w", "--workspace", "--repo", dest="workspace", default=".", help="Workspace or repository directory")
    parser.add_argument("--resume", help="Resume a persisted session ID")
    parser.add_argument("--no-parallel-tools", action="store_true", help="Disable parallel tool execution")
    parser.add_argument("--model", help="Override the OpenRouter model identifier")
    parser.add_argument("--provider", help="Override the configured provider")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        parser.error(f"Workspace does not exist: {workspace}")
    if not workspace.is_dir():
        parser.error(f"Workspace is not a directory: {workspace}")
    settings = Settings(
        workspace_root=workspace,
        provider=args.provider,
        model_name=args.model,
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
            recent_messages = previous_messages[-12:]
            while recent_messages and recent_messages[0].get("role") == "tool":
                recent_messages = recent_messages[1:]
            while recent_messages and recent_messages[-1].get("role") == "tool":
                recent_messages.pop()
                if recent_messages and recent_messages[-1].get("role") == "assistant":
                    recent_messages.pop()
            while recent_messages and recent_messages[-1].get("role") == "assistant" and recent_messages[-1].get("tool_calls"):
                recent_messages.pop()
            initial_messages.extend(recent_messages)
        loop.initial_messages = initial_messages
        try:
            result = loop.run(task_text)
        except RuntimeError as exc:
            _print_box("Forge error", str(exc), color=C_RED)
            return
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
            "phase": result.phase.value,
            "phase_history": [
                {
                    "from_phase": transition.from_phase.value,
                    "to_phase": transition.to_phase.value,
                    "reason": transition.reason,
                }
                for transition in result.phase_history
            ],
            "uncertainty": result.uncertainty,
            "blockers": result.blockers,
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
        _print_box("Forge result", result.final_answer or "No final answer was produced.")
        if result.last_error:
            print(_style("  ! Last error:", C_YELLOW), result.last_error)
        print(
            _style("  Summary ", C_BOLD),
            f"{result.usage.get('total_tokens', 0)} tokens  ·  "
            f"{result.elapsed_seconds:.2f}s  ·  session {session_id}",
        )
        print(_style("  Workspace", C_DIM), workspace)

    if args.resume:
        session = store.resume_session(args.resume)
        _print_section("Resumed session")
        print(_style("  ID", C_BOLD), args.resume)
        print(_style("  Task", C_BOLD), session["task"])
        saved_state = session.get("state", {})
        previous_messages = saved_state.get("messages", [])[-12:]
        session_summary = saved_state.get("summary", "")
        print(_style("  Summary", C_BOLD), session_summary or "No prior summary stored.")
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
        _print_workspace_preflight(workspace)
        execute(" ".join(args.task))
        return

    _print_banner(workspace)
    _print_workspace_preflight(workspace)
    while True:
        try:
            task = input(_style("forge ", C_BOLD + C_CYAN) + _style("› ", C_DIM)).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not task:
            continue
        if task.lower() in {"exit", "quit", "bye", "/exit", "/quit"}:
            return
        if task == "/help":
            _print_section("Commands")
            print("  Enter a coding task.")
            print("  /status     Show repository status")
            print("  /sessions   List saved sessions")
            print("  /history    Show tasks from this session")
            print("  /exit       Leave Forge")
            continue
        if task.lower() in {"/status", "/git-status"}:
            _print_section("Repository status")
            print(GitCheckpointManager(workspace).status()["output"])
            continue
        if task == "/sessions":
            _print_section("Sessions")
            print("\n".join(f"  {item}" for item in store.list_sessions()) or "  No sessions.")
            continue
        if task == "/history":
            _print_section("Task history")
            print("\n".join(f"  {index + 1}. {item}" for index, item in enumerate(history)) or "  No task history.")
            continue
        execute(task)


if __name__ == "__main__":
    main()
