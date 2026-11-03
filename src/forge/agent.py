from __future__ import annotations

import concurrent.futures
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .planning import PlanManager
from .prompts import PromptBuilder
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolRegistry
from .memory import compact_messages


@dataclass
class AgentState:
    """Explicit state for the agent loop."""

    task: str
    messages: list[dict[str, str]] = field(default_factory=list)
    tool_calls: int = 0
    steps: int = 0
    final_answer: str | None = None
    last_error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    tool_retries: int = 0
    plan: dict[str, Any] = field(default_factory=dict)
    modified_files: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)


class AgentLoop:
    """Minimal explicit agent loop for Milestone 1."""

    def __init__(
        self,
        model_client: Any,
        tool_registry: ToolRegistry,
        tool_dispatcher: ToolDispatcher,
        max_steps: int = 8,
        max_tool_calls: int = 10,
        debug: bool = False,
        plan_manager: PlanManager | None = None,
        prompt_builder: PromptBuilder | None = None,
        parallel_tools: bool = True,
        max_retries: int = 3,
        observability: Any | None = None,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
        initial_messages: list[dict[str, Any]] | None = None,
        max_context_tokens: int = 19000,
        memory_context_provider: Callable[[str], str] | None = None,
    ) -> None:
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.tool_dispatcher = tool_dispatcher
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.debug = debug
        self.plan_manager = plan_manager or PlanManager("")
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.parallel_tools = parallel_tools
        self.max_retries = max_retries
        self.observability = observability
        self.event_callback = event_callback
        self.initial_messages = initial_messages
        self.max_context_tokens = max_context_tokens
        self.memory_context_provider = memory_context_provider

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self.event_callback:
            self.event_callback(event, data)
        if self.observability:
            self.observability.record(event, data)

    def _trace(self, message: str) -> None:
        if self.debug:
            print(f"[TRACE] {message}")

    def run(self, task: str) -> AgentState:
        started = time.monotonic()
        safe_task = self.prompt_builder.sanitize_user_task(task)
        self.plan_manager.plan.objective = safe_task
        if not self.plan_manager.plan.steps:
            self.plan_manager.add_step("inspect repository")
            self.plan_manager.add_step("apply targeted fix")
            self.plan_manager.add_step("verify with tests")

        state = AgentState(task=safe_task)
        if self.initial_messages:
            state.messages.extend(self.initial_messages)
        memory_context = ""
        if self.memory_context_provider:
            memory_context = self.memory_context_provider(safe_task)
        state.messages.extend(self.prompt_builder.build_messages(safe_task, memory_context))
        state.messages = compact_messages(state.messages, self.max_context_tokens)

        while state.steps < self.max_steps:
            state.steps += 1
            self._trace(f"Step {state.steps}: sending model request")

            response = self.model_client.send_messages(
                messages=state.messages,
                tools=self.tool_registry.model_tools(),
            )
            self._trace(f"Model response: {response}")
            usage = response.get("usage") or {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                state.usage[key] = state.usage.get(key, 0) + int(usage.get(key, 0) or 0)
            self._emit("model_response", {"step": state.steps, "usage": usage})

            if response.get("final_answer"):
                state.final_answer = response["final_answer"]
                self._trace("Final answer received from model")
                state.elapsed_seconds = time.monotonic() - started
                self._emit("task_completed", {"elapsed_seconds": state.elapsed_seconds})
                state.plan = self.plan_manager.to_dict()
                return state

            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                legacy_single = response.get("tool_call")
                if legacy_single:
                    tool_calls = [legacy_single]

            if not tool_calls:
                state.final_answer = "The model returned no actionable result."
                state.last_error = "No tool call or final answer was returned."
                state.elapsed_seconds = time.monotonic() - started
                state.plan = self.plan_manager.to_dict()
                return state

            self._trace(f"Executing {len(tool_calls)} tool call(s): {tool_calls}")

            assistant_tool_message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": tool_call.get("id") or f"call_{index + 1}",
                        "type": "function",
                        "function": {
                            "name": tool_call["name"],
                            "arguments": json.dumps(tool_call.get("arguments", {})),
                        },
                    }
                    for index, tool_call in enumerate(tool_calls)
                ],
            }
            state.messages.append(assistant_tool_message)

            calls_to_run = tool_calls[: max(0, self.max_tool_calls - state.tool_calls)]

            def execute_with_retry(tool_call: dict[str, Any]) -> dict[str, Any]:
                result: dict[str, Any] = {"status": "error", "error": "Tool execution failed."}
                for attempt in range(self.max_retries + 1):
                    result = self.tool_dispatcher.execute(tool_call)
                    if result.get("status") != "error" or result.get("error_type") == "permission_denied":
                        return result
                    if attempt < self.max_retries:
                        state.tool_retries += 1
                        reason = str(result.get("error", "tool failed"))
                        self.plan_manager.record_failure(reason)
                        self._emit("tool_retry", {"name": tool_call.get("name"), "attempt": attempt + 1, "reason": reason})
                return result

            if self.parallel_tools and len(calls_to_run) > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(calls_to_run), 4)) as pool:
                    futures = {pool.submit(execute_with_retry, call): call for call in calls_to_run}
                    results_by_call = [future.result() for future in futures]
                    tool_results = results_by_call
            else:
                tool_results = [execute_with_retry(call) for call in calls_to_run]

            for tool_call, tool_result in zip(calls_to_run, tool_results):
                state.tool_calls += 1
                self._trace(f"Tool result: {tool_result}")
                tool_call_id = tool_call.get("id") or f"call_{state.tool_calls}"
                state.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": str(tool_result)})
                self._emit("tool_result", {"name": tool_call.get("name"), "status": tool_result.get("status")})
                if tool_result.get("status") == "error":
                    state.last_error = tool_result.get("error", "tool execution failed")
                if tool_result.get("status") == "ok":
                    tool_name = str(tool_call.get("name", ""))
                    arguments = tool_call.get("arguments", {}) or {}
                    if tool_name in {"create_file", "replace_file", "edit_file", "write_file"} and isinstance(arguments.get("path"), str):
                        state.modified_files.append(arguments["path"])
                        state.side_effects.append(tool_name)
                    if tool_name == "run_command":
                        command = arguments.get("command")
                        state.commands.append(command if isinstance(command, str) else json.dumps(command))

            if state.tool_calls >= self.max_tool_calls:
                state.final_answer = "Execution stopped because the tool call limit was reached."
                state.last_error = "Max tool call budget exceeded."
                state.elapsed_seconds = time.monotonic() - started
                state.plan = self.plan_manager.to_dict()
                return state

        state.final_answer = "The agent reached the maximum step limit before completing the task."
        state.last_error = "Max agent iteration limit reached."
        state.elapsed_seconds = time.monotonic() - started
        state.plan = self.plan_manager.to_dict()
        state.plan = self.plan_manager.to_dict()
        return state
