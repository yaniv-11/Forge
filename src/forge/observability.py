from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class RunRecorder:
    """Append-only structured trace and usage metrics for one Forge workspace."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.path = Path(workspace_root) / ".forge" / "traces.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: str, data: dict[str, Any] | None = None) -> None:
        payload = {"timestamp": time.time(), "event": event, **(data or {})}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
