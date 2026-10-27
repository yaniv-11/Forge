from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request


class OpenRouterClient:
    """Adapter for the OpenRouter-compatible chat completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: int = 30,
        site_url: str | None = None,
        app_name: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("FORGE_MODEL", "openai/gpt-4o-mini")
        self.base_url = base_url
        self.timeout = timeout
        self.site_url = site_url or os.getenv("FORGE_SITE_URL")
        self.app_name = app_name or os.getenv("FORGE_APP_NAME", "Forge")

    def send_messages(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return self._mock_response_for_tests(messages, tools)

        payload = self.build_payload(messages, tools)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name

        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw_data = response.read().decode("utf-8")
        except error.HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter API request failed: {exc.code} {response_text}") from exc

        data = json.loads(raw_data)
        parsed_tool_call = self.parse_tool_call(data)
        if parsed_tool_call:
            return {"tool_call": parsed_tool_call}

        message = (data.get("choices") or [{}])[0].get("message", {})
        content = message.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )

        return {"final_answer": str(content) if content else "OpenRouter returned no final answer."}

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
            payload["tool_choice"] = "auto"
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
        arguments = function.get("arguments", "{}")

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        return {
            "name": function.get("name"),
            "arguments": arguments,
        }


GroqClient = OpenRouterClient
