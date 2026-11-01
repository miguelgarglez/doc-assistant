from pathlib import Path
from typing import Literal

import pypdfium2 as pdfium

from doc_assistant.application.ports.pdf import Rectangle
from doc_assistant.infra.pdf.highlight import locate
from doc_assistant.infra.pdf.lock import pdf_lock


class PdfService:
    def page_count(
        self, data: bytes
    ) -> tuple[int | None, Literal["pdf_protected", "pdf_unreadable"] | None]:
        try:
            with pdf_lock:
                pdf = pdfium.PdfDocument(data)
                try:
                    return len(pdf), None
                finally:
                    pdf.close()
        except pdfium.PdfiumError as exc:
            import pypdfium2.raw as pdfium_raw  # type: ignore[import-untyped]

            reason: Literal["pdf_protected", "pdf_unreadable"] = (
                "pdf_protected"
                if exc.err_code == pdfium_raw.FPDF_ERR_PASSWORD
                else "pdf_unreadable"
            )
            return None, reason

    def locate(self, path: Path, page: int, quote: str) -> list[Rectangle] | None:
        rects = locate(path, page, quote)
        return list(rects) if rects is not None else None
