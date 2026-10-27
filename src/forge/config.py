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
        self._load_dotenv_file()

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
        if not self.debug:
            self.debug = os.getenv("FORGE_DEBUG", "false").lower() in {"1", "true", "yes", "on"}

    def _load_dotenv_file(self) -> None:
        workspace_root = Path(self.workspace_root).resolve()
        candidates = [
            workspace_root / ".env",
            Path.cwd() / ".env",
            Path(__file__).resolve().parents[2] / ".env",
        ]

        for candidate in candidates:
            if not candidate.exists():
                continue

            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = [part.strip() for part in line.split("=", 1)]
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)

            break

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
