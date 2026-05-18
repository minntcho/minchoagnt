from __future__ import annotations

import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Message:
    id: int
    session_id: str
    role: str
    content: str
    timestamp: float


class SessionDB:
    """SQLite conversation log with a small search API."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_session(self, source: str = "cli") -> str:
        session_id = uuid.uuid4().hex
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, source, started_at) VALUES (?, ?, ?)",
                (session_id, source, time.time()),
            )
        return session_id

    def append_message(self, session_id: str, role: str, content: str) -> int:
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, time.time()),
            )
            return int(cursor.lastrowid)

    def get_messages(self, session_id: str) -> list[Message]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, timestamp
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp, id
                """,
                (session_id,),
            ).fetchall()
        return [self._message(row) for row in rows]

    def search_messages(self, query: str, limit: int = 20) -> list[Message]:
        needle = query.strip()
        if not needle:
            return []
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, timestamp
                FROM messages
                WHERE lower(content) LIKE lower(?)
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (f"%{needle}%", limit),
            ).fetchall()
        return [self._message(row) for row in rows]

    def _init_schema(self) -> None:
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    started_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp)"
            )

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _message(row: sqlite3.Row) -> Message:
        return Message(
            id=int(row["id"]),
            session_id=str(row["session_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            timestamp=float(row["timestamp"]),
        )
