from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from doc_assistant.application.ports.ingest import IngestWriter
from doc_assistant.infra.storage.chunks import ChunkStore


class SqliteIngestWriterFactory:
    def __init__(self, db: Path) -> None:
        self.db = db

    def __call__(self, dim: int) -> AbstractContextManager[IngestWriter]:
        return self._open(dim)

    @contextmanager
    def _open(self, dim: int) -> Iterator[IngestWriter]:
        store = ChunkStore(self.db, dim)
        try:
            yield store
        finally:
            store.db.close()
