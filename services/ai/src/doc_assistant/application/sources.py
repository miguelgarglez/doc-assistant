from typing import Any

from doc_assistant.application.ports.sources import SourceRepository
from doc_assistant.domain.documents.ids import invoice_doc_id, pdf_doc_id


def _section_key(section: str) -> tuple[Any, ...]:
    parts = section.split(".")
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts)


class SourceService:
    def __init__(self, repository: SourceRepository) -> None:
        self.repository = repository

    def list_sources(self) -> list[dict[str, Any]]:
        snapshot = self.repository.snapshot()
        sources: list[dict[str, Any]] = []
        for doc in sorted(set(snapshot.chunks) | set(snapshot.pages)):
            rows = snapshot.chunks.get(doc, [])
            is_invoice = doc.startswith("inv-")
            name = rows[0]["display_doc"] if rows else doc.split("-", 1)[-1]
            sections = sorted(
                (
                    {
                        "section": row["section"],
                        "heading": row["heading"],
                        "pages": row["pages"],
                    }
                    for row in rows
                ),
                key=lambda section: _section_key(section["section"]),
            )
            if is_invoice:
                invoice = snapshot.invoices.get(name, {})
                file = invoice.get("fichero")
                status = "indexed" if invoice.get("cuadra") == "1" else "review"
                detail = invoice.get("motivo")
                sections = [
                    section for section in sections if section["section"] == "cabecera"
                ] or sections
            else:
                file = f"documents/{name}.pdf"
                status = "indexed" if rows else "no_text"
                detail = None if rows else "PDF sin capa de texto (necesita OCR)"
            sources.append(
                {
                    "id": doc,
                    "kind": "invoice" if is_invoice else "pdf",
                    "name": name,
                    "title": rows[0]["title"] if rows and not is_invoice else None,
                    "n_pages": snapshot.pages.get(doc, 0),
                    "n_chunks": len(rows),
                    "sections": sections,
                    "added_at": self.repository.modified_at(file) if file else None,
                    "status": status,
                    "status_detail": detail,
                    "file": file if file and self.repository.file_exists(file) else None,
                }
            )
        sources.sort(key=lambda source: (source["kind"] != "pdf", source["name"].lower()))
        return sources

    def find(self, source_id: str) -> dict[str, Any] | None:
        return next((source for source in self.list_sources() if source["id"] == source_id), None)

    def remove(self, source: dict[str, Any]) -> None:
        self.repository.remove(source)

    def chunks(self, source_id: str) -> list[dict[str, Any]]:
        return self.repository.chunks(source_id)

    def page(self, doc_id: str, page: int) -> bytes | None:
        keys = [doc_id]
        if not doc_id.startswith(("pdf-", "inv-")):
            keys.extend([pdf_doc_id(doc_id), invoice_doc_id(doc_id)])
        pages = self.repository.pages(keys, page)
        if doc_id in pages:
            return pages[doc_id]
        matches = [pages[key] for key in keys[1:] if key in pages]
        return matches[0] if len(matches) == 1 else None

    def meta_chunks(self) -> dict[str, list[dict[str, Any]]]:
        by_doc: dict[str, list[dict[str, Any]]] = {}
        for chunk in self.repository.all_chunks():
            if chunk.get("heading") and chunk["heading"] in chunk["text"]:
                by_doc.setdefault(chunk["doc"], []).append(chunk)
        for chunks in by_doc.values():
            chunks.sort(key=lambda chunk: _section_key(chunk["section"]))
        return by_doc
