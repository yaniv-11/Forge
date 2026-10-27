from forge.model_client import OpenRouterClient


def test_openrouter_client_builds_payload_and_parses_tool_calls():
    client = OpenRouterClient(api_key="test-key", model="openai/gpt-4o-mini")

    payload = client.build_payload(
        [{"role": "user", "content": "List files"}],
        [{"type": "function", "function": {"name": "list_files", "parameters": {"type": "object"}}}],
    )

    assert payload["model"] == "openai/gpt-4o-mini"
    assert payload["tool_choice"] == "auto"

    raw_response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "list_files",
                                "arguments": '{"path": "."}',
                            }
                        }
                    ]
                }
            }
        ]
    }

    parsed = client.parse_tool_call(raw_response)
    assert parsed == {"name": "list_files", "arguments": {"path": "."}}
