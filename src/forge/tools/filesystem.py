from __future__ import annotations

import re
from pathlib import Path


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


def write_file(path: str, content: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for write operations")

    target = _prepare_write_target(path, workspace_root)
    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))


def edit_file(path: str, old: str, new: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        raise ValueError("workspace_root is required for edit operations")

    target = _prepare_write_target(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    existing = target.read_text(encoding="utf-8")
    if old not in existing:
        raise ValueError(f"Target text not found in file: {path}")

    updated = existing.replace(old, new, 1)
    target.write_text(updated, encoding="utf-8")
    return str(target.relative_to(workspace_root.resolve()))
