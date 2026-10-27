from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    """Configuration for the minimal Forge runtime."""

    workspace_root: Path | str = "."
    model_name: str = "llama-3.1-8b-instant"
    api_key: str | None = None
    max_steps: int = 8
    max_tool_calls: int = 10
    timeout_seconds: int = 30
    debug: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)

    def resolve_workspace(self) -> Path:
        return Path(self.workspace_root).resolve()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self.resolve_workspace()),
            "model_name": self.model_name,
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "timeout_seconds": self.timeout_seconds,
            "debug": self.debug,
        }
