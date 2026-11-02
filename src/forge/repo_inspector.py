from __future__ import annotations

import re
import ast
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
            if (
                rel_path.startswith(".git/")
                or rel_path.startswith(".forge/")
                or rel_path.startswith(".forge_sessions/")
                or rel_path.startswith(".venv/")
                or any(part.startswith(".") for part in Path(rel_path).parts[:-1])
            ):
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
            "symbols": self.find_python_symbols(relevant, task),
            "dependencies": self.detect_dependencies(),
            "context": self.build_context(relevant),
        }

    def find_python_symbols(self, paths: list[str], task: str) -> dict[str, list[str]]:
        symbols: dict[str, list[str]] = {}
        tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9_]+", task)}
        for rel_path in paths:
            if not rel_path.endswith(".py"):
                continue
            file_path = self.workspace_root / rel_path
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            found = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if any(token in node.name.lower() for token in tokens) or not tokens:
                        found.append(node.name)
            if found:
                symbols[rel_path] = found[:20]
        return symbols

    def detect_dependencies(self) -> dict[str, list[str]]:
        names = ("pyproject.toml", "requirements.txt", "package.json", "Cargo.toml", "go.mod")
        return {
            name: (self.workspace_root / name).read_text(encoding="utf-8").splitlines()[:100]
            for name in names
            if (self.workspace_root / name).is_file()
        }

    def build_context(self, paths: list[str], max_lines: int = 40) -> dict[str, str]:
        context: dict[str, str] = {}
        for rel_path in paths[:5]:
            file_path = self.workspace_root / rel_path
            if not file_path.is_file():
                continue
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            context[rel_path] = "\n".join(lines[:max_lines])
        return context
