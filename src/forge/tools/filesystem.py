from __future__ import annotations

from pathlib import Path


def list_files(path: str = ".") -> list[str]:
    root = Path(path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return [str(item.name) for item in sorted(root.iterdir())]


def read_file(path: str) -> str:
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    return resolved.read_text(encoding="utf-8")
