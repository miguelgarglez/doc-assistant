"""Helpers for tests that check answer Markdown and inline segments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

SECTIONS = [
    ("1. Alcance", "Este documento describe la unidad demo ACME-200 y su instalación."),
    ("2. Instalación", "La base se fija con cuatro tornillos M8."),
    ("2.1. Cableado", "Usar cable de 2.5 mm2 para la alimentación principal."),
    ("2.2. Conectores", "El conector de potencia admite hasta 16 A."),
    ("3. Parada de emergencia", "La parada se completa en menos de 500 ms."),
    ("4. Mantenimiento", "Revisar los filtros cada 6 meses."),
]


def make_pdf(path: Path, title: str, sections: list[tuple[str, str]] = SECTIONS) -> Path:
    """Two-page synthetic PDF: a title, numbered sections and a footer."""
    canvas = Canvas(str(path), pagesize=A4)
    y = 800
    canvas.drawString(50, y, title)
    page = 1
    for heading, body in sections:
        if y < 120 or heading.startswith("4."):
            canvas.drawString(50, 40, f"ACME Demo · Manual · {page}")
            canvas.showPage()
            page += 1
            y = 800
        y -= 28
        canvas.drawString(50, y, heading)
        y -= 18
        canvas.drawString(50, y, body)
    canvas.drawString(50, 40, f"ACME Demo · Manual · {page}")
    canvas.showPage()
    canvas.save()
    return path


_BULLET = re.compile(r"^[-*+]\s")


def assert_valid_markdown(answer: str) -> None:
    """The structural mistakes that rendered as empty bullets and glued paragraphs."""
    lines = answer.split("\n")
    previous = ""
    for line in lines:
        assert not re.match(r"^\s*[-*+]\s*$", line), f"empty bullet in {answer!r}"
        assert not re.match(r"^\s*[-*+]\s+\d+[.)]\s", line), (
            f"bullet opens an ordered list: {line!r}"
        )
        assert not re.match(r"^\s*\d+[.)]\s", line), f"line starts a list by accident: {line!r}"
        assert not re.search(r"(?:\d+(?:\.\d+)*\.\s[^;\n]+;\s*){2,}", line), (
            f"inline numbering: {line!r}"
        )
        if line.strip() and previous.strip():
            same_block = bool(_BULLET.match(previous)) and bool(_BULLET.match(line))
            assert same_block, f"paragraphs glued without a blank line: {previous!r} / {line!r}"
        previous = line


def assert_segments_tile(result: dict[str, Any]) -> None:
    segments = result["segments"]
    assert "".join(s["text"] for s in segments) == result["answer"]
    for segment in segments:
        assert all(0 <= r < len(result["citations"]) for r in segment["refs"])
