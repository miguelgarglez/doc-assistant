import os
import re
import tempfile
from pathlib import Path

from doc_assistant.application.ports.invoice_writer import InvoiceWrite
from doc_assistant.domain.documents.ids import invoice_doc_id
from doc_assistant.infra.invoices.sqlite import FIELDS
from doc_assistant.infra.storage.chunks import ChunkStore


def sanitize_image_filename(name: str, numero: str) -> str:
    base = Path(name or f"{numero}.png").name
    safe = re.sub(r"[^\w.\-]+", "_", base, flags=re.UNICODE).strip("._") or numero
    lower = safe.lower()
    if not lower.endswith((".png", ".jpg", ".jpeg")):
        safe = f"{safe}.png"
    return safe


class SqliteInvoiceWriter:
    def __init__(self, db: Path, data_dir: Path, dim: int) -> None:
        self.db = db
        self.data_dir = data_dir
        self.dim = dim

    def save(self, invoice: InvoiceWrite) -> str:
        numero = invoice.number
        record = invoice.record
        invoices_dir = self.data_dir / "invoices"
        invoices_dir.mkdir(parents=True, exist_ok=True)
        path = invoices_dir / (
            invoice_doc_id(numero) + Path(sanitize_image_filename(invoice.filename, numero)).suffix
        )
        relative = str(path.relative_to(self.data_dir))
        fd, temporary = tempfile.mkstemp(dir=invoices_dir, prefix=".invoice-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(invoice.image)
            dim = self.dim
            store = ChunkStore(self.db, dim=dim)
            try:
                cols = ", ".join(f"{k} TEXT" for k in FIELDS)
                store.db.execute(
                    f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
                )
                values = [None if record.get(k) in (None, "") else str(record[k]) for k in FIELDS]
                placeholders = ",".join("?" * (len(FIELDS) + 3))
                store.db.execute(
                    f"INSERT OR REPLACE INTO facturas VALUES ({placeholders})",
                    [
                        *values,
                        relative,
                        "1" if invoice.state == "ok" else "0",
                        invoice.reason,
                    ],
                )
                store.replace_document(
                    invoice_doc_id(numero),
                    invoice.chunks,
                    invoice.embeddings,
                    [invoice.image],
                    commit=False,
                )
                store.db.commit()
            except Exception:
                store.db.rollback()
                raise
            finally:
                store.db.close()
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        return relative
