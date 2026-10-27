from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    ) -> None:
        self.model_client = model_client
        self.tool_registry = tool_registry
        self.tool_dispatcher = tool_dispatcher
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls

    def run(self, task: str) -> AgentState:
        state = AgentState(task=task)
        state.messages.append({"role": "user", "content": task})

        while state.steps < self.max_steps:
            state.steps += 1

            response = self.model_client.send_messages(
                messages=state.messages,
                tools=self.tool_registry.model_tools(),
            )

            if response.get("final_answer"):
                state.final_answer = response["final_answer"]
                return state

            tool_call = response.get("tool_call")
            if not tool_call:
                state.final_answer = "The model returned no actionable result."
                state.last_error = "No tool call or final answer was returned."
                return state

            if state.tool_calls >= self.max_tool_calls:
                state.final_answer = "Execution stopped because the tool call limit was reached."
                state.last_error = "Max tool call budget exceeded."
                return state

            tool_result = self.tool_dispatcher.execute(tool_call)
            state.tool_calls += 1
            state.messages.append({"role": "tool", "content": str(tool_result)})

            if tool_result.get("status") == "error":
                state.last_error = tool_result.get("error", "tool execution failed")

        state.final_answer = "The agent reached the maximum step limit before completing the task."
        state.last_error = "Max agent iteration limit reached."
        return state
