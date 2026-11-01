"""Local history storage. Nothing is recorded until a caller explicitly uses it."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any


class HistoryStore:
    """Store completed requests independently of the document index."""

    def __init__(self, path: Path) -> None:
        self.path = path
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    trace_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS requests_conversation_time
                    ON requests(conversation_id, created_at DESC, request_id DESC);
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    comment TEXT,
                    trace_json TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            yield db

    def record(
        self, request_id: str, conversation_id: str, created_at: str, trace: dict[str, Any]
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?)",
                (request_id, conversation_id, created_at, json.dumps(trace, ensure_ascii=False)),
            )

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT trace_json FROM requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_page(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        before: tuple[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], tuple[str, str] | None]:
        """Return a stable page and the position for the next page, if any."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = "SELECT created_at, request_id, trace_json FROM requests WHERE conversation_id = ?"
        params: list[Any] = [conversation_id]
        if before is not None:
            query += " AND (created_at, request_id) < (?, ?)"
            params.extend(before)
        query += " ORDER BY created_at DESC, request_id DESC LIMIT ?"
        params.append(limit + 1)
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        page = rows[:limit]
        cursor = (page[-1][0], page[-1][1]) if len(rows) > limit else None
        return [json.loads(row[2]) for row in page], cursor

    def add_feedback(
        self,
        feedback_id: str,
        request_id: str,
        created_at: str,
        kind: str,
        comment: str | None,
    ) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO feedback SELECT ?, request_id, ?, ?, ?, trace_json "
                "FROM requests WHERE request_id = ?",
                (feedback_id, created_at, kind, comment, request_id),
            )
            return cursor.rowcount == 1
