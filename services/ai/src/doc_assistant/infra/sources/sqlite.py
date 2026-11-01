import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from doc_assistant.application.ports.sources import SourceSnapshot
from doc_assistant.infra.storage.chunks import ChunkStore


class SqliteSourceRepository:
    def __init__(self, db: Path, data_dir: Path, dim: int) -> None:
        self.db = db
        self.data_dir = data_dir
        self.dim = dim

    @staticmethod
    def _invoice_rows(store: ChunkStore) -> dict[str, dict[str, Any]]:
        exists = store.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='facturas'"
        ).fetchone()
        if not exists:
            return {}
        rows = store.db.execute("SELECT numero, fichero, cuadra, motivo FROM facturas")
        return {
            row[0]: {"fichero": row[1], "cuadra": row[2], "motivo": row[3]}
            for row in rows.fetchall()
        }

    def snapshot(self) -> SourceSnapshot:
        store = ChunkStore(self.db, self.dim)
        try:
            chunks: dict[str, list[dict[str, Any]]] = {}
            for row in store.db.execute(
                "SELECT doc, display_doc, section, heading, title, pages FROM chunks"
            ):
                item = dict(row)
                item["pages"] = json.loads(item["pages"])
                chunks.setdefault(row["doc"], []).append(item)
            pages = {
                row[0]: row[1]
                for row in store.db.execute("SELECT doc, COUNT(*) FROM source_pages GROUP BY doc")
            }
            invoices = self._invoice_rows(store)
            return SourceSnapshot(chunks=chunks, pages=pages, invoices=invoices)
        finally:
            store.db.close()

    def chunks(self, source_id: str) -> list[dict[str, Any]]:
        store = ChunkStore(self.db, self.dim)
        try:
            return [
                {
                    "chunk_id": row["chunk_id"],
                    "section": row["section"],
                    "pages": json.loads(row["pages"]),
                    "text": row["body"],
                }
                for row in store.db.execute(
                    "SELECT chunk_id, section, pages, body FROM chunks "
                    "WHERE doc = ? ORDER BY rowid",
                    (source_id,),
                )
            ]
        finally:
            store.db.close()

    def pages(self, doc_ids: list[str], page: int) -> dict[str, bytes]:
        store = ChunkStore(self.db, self.dim)
        try:
            return {
                doc_id: content
                for doc_id in doc_ids
                if (content := store.page(doc_id, page)) is not None
            }
        finally:
            store.db.close()

    def all_chunks(self) -> list[dict[str, Any]]:
        store = ChunkStore(self.db, self.dim)
        try:
            return [store._row(row) for row in store.db.execute("SELECT * FROM chunks")]
        finally:
            store.db.close()

    def modified_at(self, relative: str) -> str | None:
        path = self.data_dir / relative
        if not path.is_file():
            return None
        return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")

    def file_exists(self, relative: str) -> bool:
        return (self.data_dir / relative).is_file()

    def remove(self, source: dict[str, Any]) -> None:
        store = ChunkStore(self.db, self.dim)
        try:
            store.replace_document(source["id"], [], [], [], commit=False)
            if source["kind"] == "invoice" and self._invoice_rows(store):
                store.db.execute("DELETE FROM facturas WHERE numero = ?", (source["name"],))
            store.db.commit()
        finally:
            store.db.close()
        if source["file"]:
            source_path = self.data_dir / source["file"]
            removed = self.data_dir / "_removed"
            removed.mkdir(exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            shutil.move(str(source_path), str(removed / f"{stamp}_{source_path.name}"))
