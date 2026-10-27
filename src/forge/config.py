import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    """Configuration for the minimal Forge runtime."""

    workspace_root: Path | str = "."
    provider: str = "openrouter"
    model_name: str = "openai/gpt-4o-mini"
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    site_url: str | None = None
    app_name: str | None = "Forge"
    max_steps: int = 8
    max_tool_calls: int = 10
    timeout_seconds: int = 30
    debug: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
        if self.model_name is None:
            self.model_name = os.getenv("FORGE_MODEL", "openai/gpt-4o-mini")
        if self.site_url is None:
            self.site_url = os.getenv("FORGE_SITE_URL")
        if self.app_name is None:
            self.app_name = os.getenv("FORGE_APP_NAME", "Forge")
        if self.provider is None:
            self.provider = os.getenv("FORGE_PROVIDER", "openrouter")

    def resolve_workspace(self) -> Path:
        return Path(self.workspace_root).resolve()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self.resolve_workspace()),
            "provider": self.provider,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "timeout_seconds": self.timeout_seconds,
            "debug": self.debug,
        }
