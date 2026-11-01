"""Locate a cited quote on a PDF page as rectangles, from the characters pdfium reports.

The rectangles are fractions of the page (origin at the top left), so they apply to a
rendering at any scale. Text is compared without whitespace and case, because the
quote was cut from extracted text where line breaks became spaces.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pypdfium2 as pdfium

from doc_assistant.infra.pdf.lock import pdf_lock

LINE_PAD = 0.0015


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float


def _fold(text: str) -> tuple[str, list[int]]:
    """Whitespace-free lowercase text and, per output character, its index in `text`."""
    out: list[str] = []
    origin: list[int] = []
    for i, ch in enumerate(text):
        if ch.isspace() or ch == "\u00ad":
            continue
        for piece in unicodedata.normalize("NFKC", ch).lower():
            out.append(piece)
            origin.append(i)
    return "".join(out), origin


def _same_line(box: tuple[float, float, float, float], line: list[float]) -> bool:
    _, bottom, _, top = box
    height = max(top - bottom, 1e-6)
    overlap = min(top, line[3]) - max(bottom, line[1])
    return overlap > 0.5 * height and box[0] >= line[0] - 1.0


def _line_rects(boxes: list[tuple[float, float, float, float]]) -> list[list[float]]:
    lines: list[list[float]] = []
    for box in boxes:
        if lines and _same_line(box, lines[-1]):
            current = lines[-1]
            current[0] = min(current[0], box[0])
            current[1] = min(current[1], box[1])
            current[2] = max(current[2], box[2])
            current[3] = max(current[3], box[3])
        else:
            lines.append(list(box))
    return lines


def locate_on_page(pdf: pdfium.PdfDocument, page_number: int, quote: str) -> list[Rect] | None:
    """Rectangles covering `quote` on a 1-based page, or None when the text is not there."""
    wanted, _ = _fold(quote)
    if not wanted or page_number < 1 or page_number > len(pdf):
        return None
    page = pdf[page_number - 1]
    try:
        width, height = page.get_size()
        textpage = page.get_textpage()
        try:
            text = textpage.get_text_range()
            folded, origin = _fold(text)
            starts = []
            at = folded.find(wanted)
            while at != -1:
                starts.append(at)
                at = folded.find(wanted, at + 1)
            if not starts:
                return None
            # A title also sits in the running footer; the topmost occurrence is the body one.
            candidates = []
            for at in starts:
                first, last = origin[at], origin[at + len(wanted) - 1]
                candidates.append(
                    [
                        textpage.get_charbox(i)
                        for i in range(first, last + 1)
                        if not text[i].isspace() and text[i] != "\u00ad"
                    ]
                )
            boxes = max(candidates, key=lambda found: max(box[3] for box in found))
        finally:
            textpage.close()
    finally:
        page.close()
    rects = []
    for left, bottom, right, top in _line_rects(boxes):
        rects.append(
            Rect(
                x=max(left / width - LINE_PAD, 0.0),
                y=max((height - top) / height - LINE_PAD, 0.0),
                w=min((right - left) / width + 2 * LINE_PAD, 1.0),
                h=(top - bottom) / height + 2 * LINE_PAD,
            )
        )
    return rects or None


@lru_cache(maxsize=256)
def _cached(path: str, mtime_ns: int, page_number: int, quote: str) -> tuple[Rect, ...] | None:
    with pdf_lock:
        pdf = pdfium.PdfDocument(path)
        try:
            found = locate_on_page(pdf, page_number, quote)
        finally:
            pdf.close()
    return None if found is None else tuple(found)


def locate(path: Path, page_number: int, quote: str) -> list[Rect] | None:
    found = _cached(str(path), path.stat().st_mtime_ns, page_number, quote)
    return None if found is None else list(found)
