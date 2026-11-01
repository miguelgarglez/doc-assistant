from contextlib import AbstractContextManager
from typing import Any, Protocol

from doc_assistant.application.ports.invoice_reader import InvoiceReader


class InvoiceCatalog(Protocol):
    def rows(self) -> list[dict[str, Any]]: ...
    def image(self, invoice_id: str) -> bytes | None: ...
    def open_reader(self) -> AbstractContextManager[InvoiceReader]: ...
