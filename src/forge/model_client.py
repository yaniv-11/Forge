from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


@dataclass
class ToolCall:
    """Normalized representation of a model tool call."""

    id: str | None = None
    name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    """Token accounting for a model response."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ModelResponse:
    """Provider-independent model response contract."""

    message: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: TokenUsage | None = None


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
        normalized = self.parse_model_response(data)
        if normalized.tool_calls:
            return {
                "tool_calls": [
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in normalized.tool_calls
                ],
                "finish_reason": normalized.finish_reason,
            }

        return {"final_answer": normalized.message or "OpenRouter returned no final answer."}

    def _mock_response_for_tests(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        last_user_message = messages[-1]["content"] if messages else ""

        if "list files" in last_user_message.lower():
            return {
                "tool_calls": [
                    {"id": "call_mock_1", "name": "list_files", "arguments": {"path": "."}},
                ]
            }

        if "read file" in last_user_message.lower():
            return {
                "tool_calls": [
                    {"id": "call_mock_1", "name": "read_file", "arguments": {"path": "README.md"}},
                ]
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

    def parse_model_response(self, raw_response: dict[str, Any]) -> ModelResponse:
        choices = raw_response.get("choices") or []
        if not choices:
            return ModelResponse()

        message = choices[0].get("message", {})
        if not message:
            return ModelResponse()

        tool_calls_raw = message.get("tool_calls") or []
        tool_calls = []
        for raw_call in tool_calls_raw:
            function = raw_call.get("function", {})
            arguments = function.get("arguments", "{}")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            tool_calls.append(
                ToolCall(
                    id=raw_call.get("id"),
                    name=function.get("name"),
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )

        content = message.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )

        usage = message.get("usage")
        token_usage = None
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            token_usage = TokenUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        return ModelResponse(
            message=str(content) if content else "",
            tool_calls=tool_calls,
            finish_reason=(choices[0].get("finish_reason") if len(choices) else None),
            usage=token_usage,
        )

    def parse_tool_call(self, raw_response: dict[str, Any]) -> dict[str, Any] | None:
        normalized = self.parse_model_response(raw_response)
        if not normalized.tool_calls:
            return None
        first = normalized.tool_calls[0]
        parsed = {"name": first.name, "arguments": first.arguments}
        if first.id:
            parsed["id"] = first.id
        return parsed


GroqClient = OpenRouterClient
