from __future__ import annotations

from pathlib import Path


def resolve_allowed_path(path: str, workspace_root: Path) -> Path:
    workspace_root = workspace_root.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve()

    try:
        resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace: {path}") from exc

    return resolved


def list_files(path: str = ".", workspace_root: Path | None = None) -> list[str]:
    if workspace_root is None:
        root = Path(path).resolve()
    else:
        root = resolve_allowed_path(path, workspace_root)

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return [str(item.name) for item in sorted(root.iterdir())]


def read_file(path: str, workspace_root: Path | None = None) -> str:
    if workspace_root is None:
        resolved = Path(path).resolve()
    else:
        resolved = resolve_allowed_path(path, workspace_root)

    if not resolved.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    return resolved.read_text(encoding="utf-8")
