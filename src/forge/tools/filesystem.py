from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


def resolve_allowed_path(path: str, workspace_root: Path) -> Path:
    workspace_root = workspace_root.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve(strict=False)

    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace: {path}") from exc

    for checked in (candidate, *candidate.parents):
        if checked.exists() and checked.is_symlink():
            raise ValueError(f"Refusing to use symlink path: {checked}")

    return resolved


def _prepare_write_target(path: str, workspace_root: Path) -> Path:
    resolved = resolve_allowed_path(path, workspace_root)

    if resolved.exists() and resolved.is_dir():
        raise ValueError(f"Path points to a directory, not a file: {path}")

    if resolved.exists() and resolved.is_symlink():
        raise ValueError(f"Refusing to use symlink path: {path}")

    for parent in (resolved, *resolved.parents):
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"Refusing to use symlink path: {parent}")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def list_files(path: str = ".", workspace_root: Path | None = None) -> list[str]:
    if workspace_root is None:
        root = Path(path).resolve()
    else:
        root = resolve_allowed_path(path, workspace_root)

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return [str(item.name) for item in sorted(root.iterdir())]


def search_files(
    pattern: str,
    path: str = ".",
    workspace_root: Path | None = None,
    max_results: int = 20,
) -> list[str]:
    if workspace_root is None:
        root = Path(path).resolve()
    else:
        root = resolve_allowed_path(path, workspace_root)

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                display_path = str(file_path.relative_to(workspace_root.resolve())) if workspace_root else str(file_path)
                matches.append(f"{display_path}:{line_no}:{line.strip()}")
                if len(matches) >= max_results:
                    return matches

    return matches


def read_file(path: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        resolved = Path(path).resolve()
    else:
        resolved = resolve_allowed_path(path, workspace_root)

    if not resolved.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    return resolved.read_text(encoding="utf-8")


def run_command(
    command: list[str] | str,
    cwd: str = ".",
    workspace_root: Path | None = None,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    if workspace_root is None:
        raise ValueError("workspace_root is required for command execution")

    resolved_cwd = resolve_allowed_path(cwd, workspace_root)
    if isinstance(command, str):
        argv = shlex.split(command)
    else:
        argv = list(command)

    if not argv:
        raise ValueError("Command must not be empty")

    execution_env = dict(__import__("os").environ)
    if env:
        execution_env.update(env)

    completed = subprocess.run(
        argv,
        cwd=str(resolved_cwd),
        env=execution_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "cwd": str(resolved_cwd.relative_to(workspace_root.resolve())),
    }


def create_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for create operations")

    target = _prepare_write_target(path, workspace_root)
    if target.exists():
        raise FileExistsError(f"File already exists: {path}")

    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))


def replace_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for replace operations")

    target = _prepare_write_target(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    if target.is_dir():
        raise ValueError(f"Path points to a directory, not a file: {path}")

    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))


def write_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for write operations")

    target = _prepare_write_target(path, workspace_root)
    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))


def edit_file(path: str, old: str, new: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for edit operations")
    if old == "":
        raise ValueError("Target text must not be empty")

    target = _prepare_write_target(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    existing = target.read_text(encoding="utf-8")
    occurrence_count = existing.count(old)
    if occurrence_count == 0:
        raise ValueError(f"Target text not found in file: {path}")
    if occurrence_count > 1:
        raise ValueError(
            f"Ambiguous edit: target text appears {occurrence_count} times in file: {path}. "
            "Provide a longer, unique snippet."
        )

    updated = existing.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))
