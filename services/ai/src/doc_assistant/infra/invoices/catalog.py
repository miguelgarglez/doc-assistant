from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from doc_assistant.application.ports.invoice_reader import InvoiceReader
from doc_assistant.domain.documents.ids import invoice_doc_id
from doc_assistant.infra.invoices.reader import SqliteInvoiceReader
from doc_assistant.infra.invoices.sqlite import InvoiceDB
from doc_assistant.infra.storage.chunks import ChunkStore


class SqliteInvoiceCatalog:
    def __init__(self, db: Path, data_dir: Path, dim: int) -> None:
        self.db = db
        self.data_dir = data_dir
        self.dim = dim

    def rows(self) -> list[dict[str, Any]]:
        database = InvoiceDB(str(self.db))
        try:
            return database.rows()
        finally:
            database.con.close()

    def image(self, invoice_id: str) -> bytes | None:
        database = InvoiceDB(str(self.db))
        try:
            row = database.get(invoice_id)
        finally:
            database.con.close()
        if row is None:
            return None
        store = ChunkStore(self.db, self.dim)
        try:
            image = store.page(invoice_doc_id(row["numero"]), 1)
        finally:
            store.db.close()
        if image is not None:
            return image
        file = row.get("fichero") or ""
        if file:
            path = self.data_dir / file
            if path.is_file():
                return path.read_bytes()
        return None

    @contextmanager
    def open_reader(self) -> Iterator[InvoiceReader]:
        database = InvoiceDB(str(self.db))
        try:
            yield SqliteInvoiceReader(database.con)
        finally:
            database.con.close()
