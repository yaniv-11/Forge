from __future__ import annotations

import ast
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def compact_messages(messages: list[dict[str, Any]], max_tokens: int = 12000) -> list[dict[str, Any]]:
    """Keep recent conversation while replacing older tool-heavy turns with a summary."""
    if not messages:
        return []

    total = sum(estimate_tokens(str(message.get("content", ""))) for message in messages)
    if total <= max_tokens:
        return messages

    system = [message for message in messages if message.get("role") == "system"][:1]
    non_system = [message for message in messages if message.get("role") != "system"]
    target = max(4, len(non_system))
    kept: list[dict[str, Any]] = []
    for message in reversed(non_system):
        remaining = max_tokens - sum(estimate_tokens(str(item.get("content", ""))) for item in kept)
        if kept and remaining <= 0:
            break
        kept.append(message)
        if len(kept) >= target:
            break
    kept.reverse()

    compact_count = len(non_system) - len(kept)
    omitted = non_system[:compact_count]
    details: list[str] = []
    for message in omitted:
        text = str(message.get("content", "")).strip()
        if not text:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if (
                stripped.startswith(("Task:", "Files:", "Commands:", "Failed:", "Error:", "file "))
                or "Traceback" in stripped
                or ".py" in stripped
                or ".ts" in stripped
            ):
                details.append(stripped[:300])
    detail_text = " Key details:" + " ".join(details[-12:]) if details else ""
    summary = {
        "role": "system",
        "content": (
            f"Compacted session summary: {compact_count} earlier message(s) omitted. "
            "Preserve the original task objective, completed changes, failed commands, "
            "and files that still need verification." + detail_text
        ),
    }
    return system + [summary] + kept


class WorkspaceMemory:
    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.path = self.workspace_root / ".forge" / "workspace_memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save({
                "facts": {},
                "conventions": {},
                "entrypoints": [],
                "test_commands": [],
                "known_failures": [],
            })

    def load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, memory: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(memory, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def set_fact(self, key: str, value: Any) -> None:
        memory = self.load()
        memory.setdefault("facts", {})[key] = value
        self.save(memory)

    def set_convention(self, key: str, value: Any) -> None:
        memory = self.load()
        memory.setdefault("conventions", {})[key] = value
        self.save(memory)

    def prompt_context(self) -> str:
        memory = self.load()
        sections = []
        for title, key in (
            ("Workspace facts", "facts"),
            ("Workspace conventions", "conventions"),
        ):
            values = memory.get(key, {})
            if values:
                sections.append(f"{title}: {json.dumps(values, sort_keys=True)}")
        for key in ("entrypoints", "test_commands", "known_failures"):
            values = memory.get(key, [])
            if values:
                sections.append(f"{key.replace('_', ' ').title()}: {json.dumps(values)}")
        return "\n".join(sections)


class ForgeDatabase:
    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        directory = root / ".forge"
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "memory.sqlite3"
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                messages TEXT NOT NULL DEFAULT '[]',
                plan TEXT NOT NULL DEFAULT '{}',
                usage TEXT NOT NULL DEFAULT '{}',
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                task TEXT NOT NULL,
                outcome TEXT NOT NULL,
                summary TEXT NOT NULL,
                files TEXT NOT NULL DEFAULT '[]',
                commands TEXT NOT NULL DEFAULT '[]',
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS repository_files (
                path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                language TEXT,
                summary TEXT NOT NULL DEFAULT '',
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                line INTEGER,
                signature TEXT NOT NULL DEFAULT '',
                UNIQUE(path, kind, name, line)
            );
            CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL DEFAULT 'workspace',
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source_session TEXT,
                updated_at REAL NOT NULL,
                UNIQUE(scope, category, key)
            );
            """
        )
        self.connection.commit()

    def save_session(
        self,
        session_id: str,
        task: str,
        summary: str,
        messages: list[dict[str, Any]],
        plan: dict[str, Any],
        usage: dict[str, Any],
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO sessions(id, task, summary, messages, plan, usage, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                task=excluded.task,
                summary=excluded.summary,
                messages=excluded.messages,
                plan=excluded.plan,
                usage=excluded.usage,
                updated_at=excluded.updated_at
            """,
            (
                session_id,
                task,
                summary,
                json.dumps(messages),
                json.dumps(plan),
                json.dumps(usage),
                time.time(),
            ),
        )
        self.connection.commit()

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "task": row["task"],
            "summary": row["summary"],
            "messages": json.loads(row["messages"]),
            "plan": json.loads(row["plan"]),
            "usage": json.loads(row["usage"]),
        }

    def add_episode(
        self,
        session_id: str,
        task: str,
        outcome: str,
        summary: str,
        files: Iterable[str] = (),
        commands: Iterable[str] = (),
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO episodes(session_id, task, outcome, summary, files, commands, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                task,
                outcome,
                summary,
                json.dumps(list(files)),
                json.dumps(list(commands)),
                time.time(),
            ),
        )
        self.connection.commit()

    def episodes(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {
                "session_id": row["session_id"],
                "task": row["task"],
                "outcome": row["outcome"],
                "summary": row["summary"],
                "files": json.loads(row["files"]),
                "commands": json.loads(row["commands"]),
            }
            for row in rows
        ]

    def close(self) -> None:
        self.connection.close()

    def remember(
        self,
        key: str,
        value: str,
        category: str = "fact",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self.connection.execute(
            """
            INSERT INTO memories(scope, category, key, value, source_session, updated_at)
            VALUES ('workspace', ?, ?, ?, ?, ?)
            ON CONFLICT(scope, category, key) DO UPDATE SET
                value=excluded.value,
                source_session=excluded.source_session,
                updated_at=excluded.updated_at
            """,
            (category, key, value, session_id, time.time()),
        )
        self.connection.commit()
        return {"key": key, "value": value, "category": category}

    def recall(self, limit: int = 50, category: str | None = None) -> list[dict[str, Any]]:
        if category:
            rows = self.connection.execute(
                "SELECT category, key, value FROM memories WHERE category=? ORDER BY updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT category, key, value FROM memories ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def memory_prompt_context(self, limit: int = 50) -> str:
        memories = self.recall(limit=limit)
        if not memories:
            return ""
        return "Long-term workspace memories:\n" + "\n".join(
            f"- [{memory['category']}] {memory['key']}: {memory['value']}"
            for memory in memories
        )


class RepositoryIndex:
    _IGNORED_PARTS = {".git", ".forge", ".forge_sessions", ".venv", "__pycache__", "node_modules"}
    _SUFFIXES = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cs", ".md", ".json", ".toml"}

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.database = ForgeDatabase(self.workspace_root)

    def rebuild(self, max_files: int = 2000) -> dict[str, int]:
        indexed_files = 0
        indexed_symbols = 0
        for file_path in sorted(self.workspace_root.rglob("*")):
            if indexed_files >= max_files:
                break
            if not file_path.is_file() or file_path.suffix.lower() not in self._SUFFIXES:
                continue
            if any(part in self._IGNORED_PARTS for part in file_path.parts):
                continue
            relative = file_path.relative_to(self.workspace_root).as_posix()
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            content_hash = str(abs(hash(content)))
            self.database.connection.execute(
                """
                INSERT INTO repository_files(path, content_hash, language, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET content_hash=excluded.content_hash,
                    language=excluded.language, updated_at=excluded.updated_at
                """,
                (relative, content_hash, file_path.suffix.lower().lstrip("."), time.time()),
            )
            indexed_files += 1
            if file_path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue
                self.database.connection.execute("DELETE FROM symbols WHERE path = ?", (relative,))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        kind = "class" if isinstance(node, ast.ClassDef) else "function"
                        signature = node.name
                        self.database.connection.execute(
                            "INSERT OR IGNORE INTO symbols(path, kind, name, line, signature) VALUES (?, ?, ?, ?, ?)",
                            (relative, kind, node.name, getattr(node, "lineno", None), signature),
                        )
                        indexed_symbols += 1
        self.database.connection.commit()
        return {"files": indexed_files, "symbols": indexed_symbols}

    def find_symbols(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = self.database.connection.execute(
            """
            SELECT path, kind, name, line, signature FROM symbols
            WHERE lower(name) LIKE ? ORDER BY name LIMIT ?
            """,
            (f"%{query.lower()}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def prompt_context(self, task: str, limit_files: int = 8, limit_symbols: int = 20) -> str:
        words = {
            word.lower()
            for word in re.findall(r"[A-Za-z0-9_]+", task)
            if len(word) > 2
        }
        if not words:
            return ""
        placeholders = ",".join("?" for _ in words)
        parameters: list[Any] = [f"%{word}%" for word in words]
        rows = self.database.connection.execute(
            f"""
            SELECT path FROM repository_files
            WHERE {' OR '.join('lower(path) LIKE ?' for _ in words)}
            LIMIT {limit_files}
            """,
            parameters,
        ).fetchall()
        symbol_rows = self.database.connection.execute(
            f"""
            SELECT path, kind, name, line, signature FROM symbols
            WHERE {' OR '.join('lower(name) LIKE ?' for _ in words)}
            ORDER BY name LIMIT ?
            """,
            parameters + [limit_symbols],
        ).fetchall()
        sections = []
        if rows:
            sections.append("Repository files relevant to this task:\n- " + "\n- ".join(row["path"] for row in rows))
        if symbol_rows:
            sections.append(
                "Relevant repository symbols:\n"
                + "\n".join(
                    f"- {row['path']}:{row['line']} {row['kind']} {row['name']}"
                    for row in symbol_rows
                )
            )
        return "\n".join(sections)

    def close(self) -> None:
        self.database.close()
