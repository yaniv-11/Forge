from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class SessionStore:
    """Persist agent session state and resume safely without replaying destructive side effects."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_session(self, task: str, state: dict[str, Any] | None = None) -> str:
        existing = [path.stem for path in self.root.glob("session-*.json")]
        numbers = [int(name.split("-", 1)[1]) for name in existing if name.split("-", 1)[-1].isdigit()]
        session_id = f"session-{max(numbers, default=-1) + 1}"
        payload = {"task": task, "state": state or {}, "side_effects": []}
        path = self.root / f"{session_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return session_id

    def load_session(self, session_id: str) -> dict[str, Any]:
        path = self.root / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown session: {session_id}")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def resume_session(self, session_id: str) -> dict[str, Any]:
        payload = self.load_session(session_id)
        side_effects = payload.get("state", {}).get("side_effects", [])
        if side_effects:
            raise ValueError("Refusing to resume after destructive side effects without explicit approval.")
        return payload

    def update_session(self, session_id: str, state: dict[str, Any]) -> dict[str, Any]:
        payload = self.load_session(session_id)
        payload["state"].update(state)
        path = self.root / f"{session_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(temporary, path)
        return payload

    def list_sessions(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("session-*.json"))
