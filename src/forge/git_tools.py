from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class GitCheckpointManager:
    """Create conservative Git checkpoints without auto-discarding unrelated work."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=check,
        )

    def create_checkpoint(self, message: str) -> dict[str, Any]:
        try:
            self._git("rev-parse", "--is-inside-work-tree")
        except subprocess.CalledProcessError:
            return {"status": "error", "error": "Not a Git repository."}

        tag = f"forge-checkpoint-{abs(hash(message)) % 1000000000}"
        try:
            self._git("tag", tag, "-m", message)
        except subprocess.CalledProcessError:
            return {"status": "error", "error": "Git checkpoint creation failed."}
        return {"status": "ok", "path": str(self.repo_path), "tag": tag}

    def restore_checkpoint(self, checkpoint: str) -> dict[str, Any]:
        try:
            self._git("rev-parse", "--is-inside-work-tree")
        except subprocess.CalledProcessError:
            return {"status": "error", "error": "Not a Git repository."}

        try:
            self._git("checkout", checkpoint, "--", ".")
        except subprocess.CalledProcessError:
            return {"status": "error", "error": f"Checkpoint {checkpoint!r} not found."}

        return {"status": "ok", "checkpoint": checkpoint}
