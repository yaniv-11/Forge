from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class RepositoryInspector:
    """Scores repository files by their relevance to a task description."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def inspect(self, task: str, max_files: int = 10) -> dict[str, Any]:
        task_tokens = {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9_]+", task)
            if len(token) > 2
        }
        candidates: list[tuple[int, str]] = []

        for file_path in sorted(self.workspace_root.rglob("*")):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(self.workspace_root).as_posix()
            if rel_path.startswith(".git/") or any(part.startswith(".") for part in Path(rel_path).parts[:-1]):
                continue

            score = 0
            lower_name = file_path.name.lower()
            lower_rel = rel_path.lower()
            for token in task_tokens:
                if token in lower_name or token in lower_rel:
                    score += 3
                if token in lower_rel.split("/"):
                    score += 2
            if "test" in lower_name or "/test" in lower_rel:
                score -= 2
            if lower_name.endswith((".py", ".ts", ".js", ".md")):
                score += 1
            if lower_rel.startswith("docs/"):
                score -= 1
            if lower_name.startswith("test_"):
                score -= 1
            if score > 0:
                candidates.append((score, rel_path))

        if not candidates:
            relevant = [
                file_path.relative_to(self.workspace_root).as_posix()
                for file_path in sorted(self.workspace_root.rglob("*"))
                if file_path.is_file() and not file_path.name.startswith(".")
            ][:max_files]
        else:
            ranked = sorted(candidates, key=lambda item: (-item[0], item[1]))
            relevant = [rel_path for _, rel_path in ranked[:max_files]]

        return {
            "task": task,
            "relevant_paths": relevant,
            "total_candidates": len(candidates),
        }
