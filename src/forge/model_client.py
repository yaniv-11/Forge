from __future__ import annotations

import json
from typing import Any


class GroqClient:
    """Adapter for the Groq API. This is intentionally thin and isolated."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.1-8b-instant",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def send_messages(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response_for_tests(messages, tools)

        raise NotImplementedError("Live Groq API integration is not implemented in Milestone 1.")

    def _mock_response_for_tests(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        last_user_message = messages[-1]["content"] if messages else ""

        if "list files" in last_user_message.lower():
            return {
                "tool_call": {
                    "name": "list_files",
                    "arguments": {"path": "."},
                }
            }

        if "read file" in last_user_message.lower():
            return {
                "tool_call": {
                    "name": "read_file",
                    "arguments": {"path": "README.md"},
                }
            }

        return {"final_answer": "Mock model response: task was acknowledged and handled without a live API call."}

    def build_payload(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            payload["tools"] = tools
        return payload

    def parse_tool_call(self, raw_response: dict[str, Any]) -> dict[str, Any] | None:
        choices = raw_response.get("choices") or []
        if not choices:
            return None

        message = choices[0].get("message", {})
        if not message:
            return None

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return None

        first = tool_calls[0]
        function = first.get("function", {})
        return {
            "name": function.get("name"),
            "arguments": json.loads(function.get("arguments", "{}")),
        }
