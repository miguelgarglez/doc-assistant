"""Valid Markdown for template answers, with one citation per answer element.

Template answers (meta questions and SQL invoice answers) are built from blocks.
Each block is a paragraph or a bullet and may carry citations. The same blocks
yield the Markdown text and the inline segments, so a marker always sits on the
element it supports. The segment texts concatenate to the answer exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_SPECIAL = re.compile(r"([\\`*_{}\[\]<>|~#])")
_LEADING = re.compile(r"^(\s*)(\d+)([.)])(?=\s)")
_LEADING_MARK = re.compile(r"^(\s*)([-+=])(?=\s)")


def md_escape(text: str) -> str:
    """Escape text that comes from data so it renders literally inside Markdown."""
    escaped = _SPECIAL.sub(r"\\\1", text)
    escaped = _LEADING.sub(r"\1\2\\\3", escaped)
    return _LEADING_MARK.sub(r"\1\\\2", escaped)


_HEADING_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$")


def split_heading(heading: str) -> tuple[str | None, str]:
    """ "2.1. Cableado" becomes ("2.1", "Cableado"); a heading without a number stays whole."""
    match = _HEADING_NUMBER.match(heading.strip())
    if match:
        return match.group(1), match.group(2)
    return None, heading.strip()


def section_label(heading: str) -> str:
    """Escaped label that never starts with a list-like number: "§2.1 Cableado"."""
    number, title = split_heading(heading)
    return f"§{number} {md_escape(title)}" if number else md_escape(title)


@dataclass
class _Block:
    text: str
    bullet: bool
    refs: list[int]


@dataclass
class AnswerBuilder:
    """Collects blocks and citations; `build` returns answer, citations and segments."""

    citations: list[dict[str, Any]] = field(default_factory=list)
    _blocks: list[_Block] = field(default_factory=list)

    def cite(self, citation: dict[str, Any]) -> int:
        for i, existing in enumerate(self.citations):
            if (
                existing["chunk_id"] == citation["chunk_id"]
                and existing["quote"] == citation["quote"]
            ):
                return i
        self.citations.append(citation)
        return len(self.citations) - 1

    def paragraph(self, text: str, cites: list[dict[str, Any]] | None = None) -> None:
        self._blocks.append(_Block(text, False, [self.cite(c) for c in cites or []]))

    def bullet(self, text: str, cites: list[dict[str, Any]] | None = None) -> None:
        self._blocks.append(_Block(text, True, [self.cite(c) for c in cites or []]))

    def build(self) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
        answer = ""
        segments: list[dict[str, Any]] = []
        previous: _Block | None = None
        for block in self._blocks:
            if previous is None:
                separator = ""
            elif block.bullet and previous.bullet:
                separator = "\n"
            else:
                separator = "\n\n"
            piece = ("- " if block.bullet else "") + block.text
            segments.append({"text": separator + piece, "refs": list(block.refs)})
            answer += separator + piece
            previous = block
        return answer, list(self.citations), segments
