from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .planning import PlanManager
from .prompts import PromptBuilder
from .tool_dispatcher import ToolDispatcher
from .tool_registry import ToolRegistry


@dataclass
class AgentState:
    """Explicit state for the agent loop."""

    task: str
    messages: list[dict[str, str]] = field(default_factory=list)
    tool_calls: int = 0
    steps: int = 0
    final_answer: str | None = None
    last_error: str | None = None


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
    ) -> None:
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.tool_dispatcher = tool_dispatcher
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.debug = debug
        self.plan_manager = plan_manager or PlanManager("")
        self.prompt_builder = prompt_builder or PromptBuilder()

    def _trace(self, message: str) -> None:
        if self.debug:
            print(f"[TRACE] {message}")

    def run(self, task: str) -> AgentState:
        safe_task = self.prompt_builder.sanitize_user_task(task)
        self.plan_manager.plan.objective = safe_task
        if not self.plan_manager.plan.steps:
            self.plan_manager.add_step("inspect repository")
            self.plan_manager.add_step("apply targeted fix")
            self.plan_manager.add_step("verify with tests")

        state = AgentState(task=safe_task)
        state.messages.extend(self.prompt_builder.build_messages(safe_task))

        while state.steps < self.max_steps:
            state.steps += 1
            self._trace(f"Step {state.steps}: sending model request")

            response = self.model_client.send_messages(
                messages=state.messages,
                tools=self.tool_registry.model_tools(),
            )
            self._trace(f"Model response: {response}")

            if response.get("final_answer"):
                state.final_answer = response["final_answer"]
                self._trace("Final answer received from model")
                return state

            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                legacy_single = response.get("tool_call")
                if legacy_single:
                    tool_calls = [legacy_single]

            if not tool_calls:
                state.final_answer = "The model returned no actionable result."
                state.last_error = "No tool call or final answer was returned."
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

            for tool_call in tool_calls:
                if state.tool_calls >= self.max_tool_calls:
                    state.final_answer = "Execution stopped because the tool call limit was reached."
                    state.last_error = "Max tool call budget exceeded."
                    return state

                tool_result = self.tool_dispatcher.execute(tool_call)
                state.tool_calls += 1
                self._trace(f"Tool result: {tool_result}")

                tool_call_id = tool_call.get("id") or f"call_{state.tool_calls}"
                state.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(tool_result),
                    }
                )

                if tool_result.get("status") == "error":
                    state.last_error = tool_result.get("error", "tool execution failed")

            if state.tool_calls >= self.max_tool_calls:
                continue

        state.final_answer = "The agent reached the maximum step limit before completing the task."
        state.last_error = "Max agent iteration limit reached."
        return state
