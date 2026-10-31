"""SQLite: tabla chunks + FTS5 + sqlite-vec (coseno); upsert por chunk_id."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import sqlite_vec

from doc_assistant.adapters import serialize_f32
from doc_assistant.config import load_config

_STOP = {
    "el",
    "la",
    "los",
    "las",
    "de",
    "del",
    "a",
    "en",
    "y",
    "o",
    "que",
    "qué",
    "cuál",
    "cuáles",
    "es",
    "son",
    "se",
    "un",
    "una",
    "por",
    "para",
    "con",
    "al",
    "su",
    "sus",
    "cada",
    "como",
    "cuánto",
    "cuántos",
    "cuánta",
    "hay",
    "debe",
}


def fts_query(q: str) -> str:
    toks = re.findall(r"\w+", q.lower())
    parts = [f'"{t}"' for t in toks if t not in _STOP and len(t) > 1]
    return " OR ".join(parts) if parts else '""'


# Súbelo cuando cambie el esquema de chunks/vec/pages/facturas. Un índice antiguo no
# se migra: se aparta (renombrado, no borrado) y se recrea; basta reingestar.
SCHEMA_VERSION = 2


def ensure_schema(path: str | Path) -> None:
    """Aparta un .db con otra versión de esquema a `<db>.schema-v<N>.bak`."""
    p = Path(path)
    if str(path) == ":memory:" or not p.exists():
        return
    con = sqlite3.connect(str(p))
    try:
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        has_tables = (
            con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] > 0
        )
    finally:
        con.close()
    if has_tables and version != SCHEMA_VERSION:
        backup = p.with_name(f"{p.name}.schema-v{version}.bak")
        p.replace(backup)
        print(
            f"[store] índice con esquema v{version} apartado en {backup}; reingesta los documentos"
        )


class ChunkStore:
    def __init__(self, path: str | Path, dim: int) -> None:
        self.path = Path(path)
        self.dim = dim
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ensure_schema(self.path)
        self.db = sqlite3.connect(str(self.path))
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        self.db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @classmethod
    def from_config(cls, config_path: str | Path) -> ChunkStore:
        cfg = load_config(config_path)
        dim = cfg.embeddings.dim or 8
        return cls(cfg.db, dim=dim)

    def _init_schema(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc TEXT NOT NULL,
                display_doc TEXT NOT NULL,
                section TEXT NOT NULL,
                heading TEXT,
                title TEXT,
                pages TEXT NOT NULL,
                body TEXT NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS source_pages (doc TEXT, page INTEGER, png BLOB NOT NULL, PRIMARY KEY(doc, page))"
        )
        # FTS5 and vec0 cannot easily ALTER; create if missing.
        row = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fts'"
        ).fetchone()
        if not row:
            self.db.execute(
                "CREATE VIRTUAL TABLE fts USING fts5("
                "chunk_id UNINDEXED, text, "
                "tokenize='unicode61 remove_diacritics 2')"
            )
        row = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vec'"
        ).fetchone()
        if not row:
            self.db.execute(
                f"CREATE VIRTUAL TABLE vec USING vec0("
                f"chunk_id TEXT PRIMARY KEY, "
                f"emb float[{self.dim}] distance_metric=cosine)"
            )
        self.db.commit()

    def upsert(
        self, chunks: list[dict[str, Any]], embeddings: list[list[float]], *, commit: bool = True
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks y embeddings deben tener la misma longitud")
        for c, e in zip(chunks, embeddings):
            self.db.execute(
                """
                INSERT INTO chunks(chunk_id, doc, display_doc, section, heading, title, pages, body, text)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    doc=excluded.doc,
                    display_doc=excluded.display_doc,
                    section=excluded.section,
                    heading=excluded.heading,
                    title=excluded.title,
                    pages=excluded.pages,
                    body=excluded.body,
                    text=excluded.text
                """,
                (
                    c["chunk_id"],
                    c["doc"],
                    c.get("display_doc", c["doc"]),
                    c["section"],
                    c.get("heading"),
                    c.get("title"),
                    json.dumps(c.get("pages") or []),
                    c["body"],
                    c["text"],
                ),
            )
            # FTS5 / vec0: delete + insert for idempotent replace
            self.db.execute("DELETE FROM fts WHERE chunk_id = ?", (c["chunk_id"],))
            self.db.execute(
                "INSERT INTO fts(chunk_id, text) VALUES(?, ?)", (c["chunk_id"], c["text"])
            )
            self.db.execute("DELETE FROM vec WHERE chunk_id = ?", (c["chunk_id"],))
            self.db.execute(
                "INSERT INTO vec(chunk_id, emb) VALUES(?, ?)",
                (c["chunk_id"], serialize_f32(e)),
            )
        if commit:
            self.db.commit()

    def replace_document(
        self,
        doc: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
        pages: list[bytes],
        *,
        commit: bool = True,
    ) -> None:
        """Replace all derived state for a document in one transaction."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        try:
            ids = [
                row[0]
                for row in self.db.execute("SELECT chunk_id FROM chunks WHERE doc = ?", (doc,))
            ]
            for cid in ids:
                self.db.execute("DELETE FROM fts WHERE chunk_id = ?", (cid,))
                self.db.execute("DELETE FROM vec WHERE chunk_id = ?", (cid,))
            self.db.execute("DELETE FROM chunks WHERE doc = ?", (doc,))
            self.db.execute("DELETE FROM source_pages WHERE doc = ?", (doc,))
            self.db.executemany(
                "INSERT INTO source_pages VALUES (?, ?, ?)",
                [(doc, i, data) for i, data in enumerate(pages, 1)],
            )
            self.upsert(chunks, embeddings, commit=commit)
        except Exception:
            self.db.rollback()
            raise

    def page(self, doc: str, n: int) -> bytes | None:
        row = self.db.execute(
            "SELECT png FROM source_pages WHERE doc = ? AND page = ?", (doc, n)
        ).fetchone()
        return bytes(row[0]) if row else None

    def count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        row = self.db.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return self._row(row) if row else None

    def get_by_section(self, section: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT * FROM chunks WHERE section = ? LIMIT 1", (section,)
        ).fetchone()
        if not row:
            raise KeyError(f"section {section!r} not found")
        return self._row(row)

    def get_many(self, chunk_ids: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for cid in chunk_ids:
            c = self.get(cid)
            if c:
                out[cid] = c
        return out

    def bm25(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        fq = fts_query(query)
        if fq == '""':
            return []
        try:
            rows = self.db.execute(
                "SELECT chunk_id, -bm25(fts) AS score FROM fts "
                "WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?",
                (fq, k),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [(r["chunk_id"], float(r["score"])) for r in rows]

    def vector_search(self, query_emb: list[float], k: int = 10) -> list[tuple[str, float]]:
        rows = self.db.execute(
            "SELECT chunk_id, distance FROM vec WHERE emb MATCH ? AND k = ? ORDER BY distance",
            (serialize_f32(query_emb), k),
        ).fetchall()
        # distance es NULL si algún vector tiene norma 0 (coseno indefinido): similitud 0.
        return [
            (r["chunk_id"], 0.0 if r["distance"] is None else 1.0 - float(r["distance"]))
            for r in rows
        ]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["pages"] = json.loads(d["pages"]) if isinstance(d["pages"], str) else d["pages"]
        return d
