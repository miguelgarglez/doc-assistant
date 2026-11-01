import hashlib
import json
from pathlib import Path

from doc_assistant.application.ports.retrieval import RetrievalResult
from doc_assistant.infra.storage.chunks import ChunkStore


class SqliteRetrievalIndex:
    def __init__(self, db: Path, dim: int) -> None:
        self.db = db
        self.dim = dim

    def search(
        self, embedding: list[float], question: str, *, fingerprint: bool
    ) -> RetrievalResult:
        store = ChunkStore(self.db, dim=self.dim)
        try:
            index_sha256 = None
            schema_version = None
            if fingerprint:
                store.db.execute("BEGIN")
                digest = hashlib.sha256()
                for row in store.db.execute(
                    "SELECT chunk_id, doc, display_doc, section, heading, title, pages, body, text "
                    "FROM chunks ORDER BY chunk_id"
                ):
                    digest.update(json.dumps(list(row), ensure_ascii=False).encode("utf-8"))
                    digest.update(b"\n")
                index_sha256 = digest.hexdigest()
                schema_version = store.db.execute("PRAGMA user_version").fetchone()[0]
            vector = store.vector_search(embedding, k=10)
            keyword = store.bm25(question, k=10)
            ids = list(dict.fromkeys(cid for cid, _ in vector + keyword))
            chunks = store.get_many(ids)
            return RetrievalResult(vector, keyword, chunks, index_sha256, schema_version)
        finally:
            store.db.close()
