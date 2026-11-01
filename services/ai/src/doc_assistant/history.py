"""Local history storage. Nothing is recorded until a caller explicitly uses it."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any


class HistoryStore:
    """Store completed requests independently of the document index."""

    def __init__(self, path: Path) -> None:
        self.path = path
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        with self._connect() as db:
            deadline = time.monotonic() + 10
            while True:
                try:
                    db.execute("PRAGMA journal_mode=WAL")
                    break
                except sqlite3.OperationalError as exc:
                    if exc.sqlite_errorcode != sqlite3.SQLITE_BUSY or time.monotonic() >= deadline:
                        raise
                    time.sleep(0.01)
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
                    conversation_id TEXT,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    comment TEXT,
                    status TEXT NOT NULL DEFAULT 'nuevo',
                    expected_answer TEXT,
                    trace_json TEXT NOT NULL
                );
                """
            )
            db.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in db.execute("PRAGMA table_info(feedback)")}
            if "conversation_id" not in columns:
                db.execute("ALTER TABLE feedback ADD COLUMN conversation_id TEXT")
                db.execute(
                    "UPDATE feedback SET conversation_id = "
                    "(SELECT conversation_id FROM requests WHERE requests.request_id = feedback.request_id)"
                )
            if "status" not in columns:
                db.execute("ALTER TABLE feedback ADD COLUMN status TEXT NOT NULL DEFAULT 'nuevo'")
            if "expected_answer" not in columns:
                db.execute("ALTER TABLE feedback ADD COLUMN expected_answer TEXT")
            db.execute(
                "CREATE INDEX IF NOT EXISTS feedback_conversation_time "
                "ON feedback(conversation_id, created_at DESC, feedback_id DESC)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            yield db

    def record(
        self, request_id: str, conversation_id: str, created_at: str, trace: dict[str, Any]
    ) -> None:
        if "request_id" in trace and trace["request_id"] != request_id:
            raise ValueError("trace request_id does not match the request")
        with self._connect() as db:
            db.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?)",
                (request_id, conversation_id, created_at, json.dumps(trace, ensure_ascii=False)),
            )

    def get(self, conversation_id: str, request_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT trace_json FROM requests WHERE conversation_id = ? AND request_id = ?",
                (conversation_id, request_id),
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
        conversation_id: str,
        request_id: str,
        created_at: str,
        kind: str,
        comment: str | None,
    ) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO feedback (feedback_id, request_id, conversation_id, created_at, kind, comment, trace_json) "
                "SELECT ?, request_id, conversation_id, ?, ?, ?, trace_json "
                "FROM requests WHERE conversation_id = ? AND request_id = ?",
                (feedback_id, created_at, kind, comment, conversation_id, request_id),
            )
            return cursor.rowcount == 1

    def list_feedback_page(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
        before: tuple[str, str] | None = None,
    ) -> tuple[list[dict[str, Any]], tuple[str, str] | None]:
        """List feedback snapshots for one conversation, newest first."""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        query = (
            "SELECT feedback_id, request_id, created_at, kind, comment, trace_json, status, expected_answer "
            "FROM feedback WHERE conversation_id = ?"
        )
        params: list[Any] = [conversation_id]
        if before is not None:
            query += " AND (created_at, feedback_id) < (?, ?)"
            params.extend(before)
        query += " ORDER BY created_at DESC, feedback_id DESC LIMIT ?"
        params.append(limit + 1)
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        page = rows[:limit]
        cursor = (page[-1][2], page[-1][0]) if len(rows) > limit else None
        return [self._feedback_row(row) for row in page], cursor

    @staticmethod
    def _feedback_row(row: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "feedback_id": row[0],
            "request_id": row[1],
            "created_at": row[2],
            "kind": row[3],
            "comment": row[4],
            "trace": json.loads(row[5]),
            "status": row[6],
            "expected_answer": row[7],
        }

    def get_feedback(self, conversation_id: str, feedback_id: str) -> dict[str, Any] | None:
        """Read the server snapshot, including after its request has been removed."""
        with self._connect() as db:
            row = db.execute(
                "SELECT feedback_id, request_id, created_at, kind, comment, trace_json, status, expected_answer "
                "FROM feedback WHERE conversation_id = ? AND feedback_id = ?",
                (conversation_id, feedback_id),
            ).fetchone()
        if row is None:
            return None
        return self._feedback_row(row)

    def set_feedback_status(self, conversation_id: str, feedback_id: str, status: str) -> bool:
        """Update a feedback review state within its conversation."""
        if status not in {"nuevo", "revisado", "convertido a caso", "descartado"}:
            raise ValueError("invalid feedback status")
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE feedback SET status = ? WHERE conversation_id = ? AND feedback_id = ?",
                (status, conversation_id, feedback_id),
            )
            return cursor.rowcount == 1

    def set_expected_answer(
        self, conversation_id: str, feedback_id: str, answer: str | None
    ) -> bool:
        """Save the reviewer's expected answer without changing the captured trace."""
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE feedback SET expected_answer = ? WHERE conversation_id = ? AND feedback_id = ?",
                (answer, conversation_id, feedback_id),
            )
            return cursor.rowcount == 1

    def export_reviewed(self, conversation_id: str) -> Iterator[str]:
        """Yield JSONL drafts with an expected answer, never approved gold cases."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT feedback_id, request_id, created_at, kind, comment, trace_json, status, expected_answer "
                "FROM feedback WHERE conversation_id = ? AND status = 'revisado' "
                "AND expected_answer IS NOT NULL AND length(trim(expected_answer)) > 0 "
                "ORDER BY created_at, feedback_id",
                (conversation_id,),
            )
            for row in rows:
                yield json.dumps(self._feedback_row(row), ensure_ascii=False) + "\n"
