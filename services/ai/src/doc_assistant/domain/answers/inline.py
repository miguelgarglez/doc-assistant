"""Inline citation segments: which verified citation supports which part of an answer.

A segment is a piece of the answer plus `refs`, positions in the citation list. The
segment texts always concatenate to the answer. Two sources produce them. The model
may emit them, and `validate_model_segments` accepts them only when every id exists
and every cited fragment supports its segment. Otherwise `assign_by_rules` places a
citation on a sentence only when the sentence shares its quantities and enough of
its content words with that fragment. A segment without support gets no marker.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from doc_assistant.domain.answers.verifier import quantities_supported

Segment = dict[str, Any]

MIN_OVERLAP = 0.5
_STEM = 5
_STOP = frozenset(
    [
        "para",
        "como",
        "pero",
        "porque",
        "cuando",
        "donde",
        "sobre",
        "entre",
        "desde",
        "hasta",
        "este",
        "esta",
        "estos",
        "estas",
        "ese",
        "esa",
        "esos",
        "esas",
        "segun",
        "tiene",
        "tienen",
        "puede",
        "pueden",
        "debe",
        "deben",
        "cada",
        "todo",
        "toda",
        "todos",
        "todas",
        "otro",
        "otra",
        "otros",
        "otras",
        "mas",
        "menos",
        "muy",
        "tambien",
        "solo",
        "sino",
        "aunque",
        "mientras",
        "durante",
        "cual",
        "cuales",
        "que",
        "del",
        "los",
        "las",
        "una",
        "uno",
        "unos",
        "unas",
        "con",
        "por",
        "sus",
        "son",
        "hay",
        "ser",
        "sea",
        "esta",
        "estan",
    ]
)
_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def stems(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _fold(text))
    return {w[:_STEM] for w in words if len(w) >= 4 and w not in _STOP and not w.isdigit()}


def overlap(text: str, fragment: str) -> float:
    """Share of the text's content stems found in the fragment (1.0 when it has none)."""
    wanted = stems(text)
    if not wanted:
        return 1.0
    return len(wanted & stems(fragment)) / len(wanted)


def supports(text: str, fragments: list[str]) -> bool:
    """The fragments cover the text's quantities and enough of its content words."""
    if not quantities_supported(text, fragments):
        return False
    return overlap(text, " ".join(fragments)) >= MIN_OVERLAP


def split_sentences(answer: str) -> list[str]:
    """Pieces that concatenate back to `answer`; each keeps the whitespace before it."""
    pieces: list[str] = []
    last = 0
    for match in _BOUNDARY.finditer(answer):
        pieces.append(answer[last : match.start()])
        last = match.start()
    pieces.append(answer[last:])
    return [p for p in pieces if p]


def _reorder(
    citations: list[dict[str, Any]], segments: list[Segment]
) -> tuple[list[dict[str, Any]], list[Segment]]:
    """Keep only cited positions, in order of first use, so markers read 1, 2, 3 along the text.

    A citation no sentence uses supports nothing the reader can see, so it is dropped. When no
    sentence got a marker the list stays as it is and the sources go after the answer.
    """
    order: list[int] = []
    for segment in segments:
        for ref in segment["refs"]:
            if ref not in order:
                order.append(ref)
    if not order:
        order = list(range(len(citations)))
    position = {old: new for new, old in enumerate(order)}
    return (
        [citations[i] for i in order],
        [{"text": s["text"], "refs": [position[r] for r in s["refs"]]} for s in segments],
    )


def _fragments(citations: list[dict[str, Any]], refs: list[int]) -> list[str]:
    return [citations[r]["fragment"] for r in refs]


def assign_by_rules(
    answer: str, citations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[Segment]]:
    segments: list[Segment] = []
    for sentence in split_sentences(answer):
        scored = [
            (overlap(sentence, c["fragment"]), i)
            for i, c in enumerate(citations)
            if supports(sentence, [c["fragment"]])
        ]
        best = max((score for score, _ in scored), default=0.0)
        refs = sorted(i for score, i in scored if score >= best - 0.1)[:2]
        segments.append({"text": sentence, "refs": refs})
    return _reorder(citations, segments)


def validate_model_segments(
    answer: str,
    raw: Any,
    citations: list[dict[str, Any]],
    ids: list[str],
) -> tuple[list[dict[str, Any]], list[Segment]] | None:
    """Accept the model's segments or return None.

    `ids[i]` is the chunk id of `citations[i]`. None means the structure is wrong: a
    non-list, a segment text that is not in the answer in order, or an unknown id. A
    segment whose fragments do not support its text keeps no refs.
    """
    if not isinstance(raw, list) or not raw:
        return None
    segments: list[Segment] = []
    cursor = 0
    for item in raw:
        if not isinstance(item, dict):
            return None
        text, chunk_ids = item.get("text"), item.get("chunk_ids")
        if not isinstance(text, str) or not text.strip() or not isinstance(chunk_ids, list):
            return None
        start = answer.find(text.strip(), cursor)
        if start == -1:
            return None
        if any(not isinstance(c, str) or c not in ids for c in chunk_ids):
            return None
        if answer[cursor:start].strip():
            segments.append({"text": answer[cursor:start], "refs": []})
            cursor = start
        end = start + len(text.strip())
        refs = sorted({ids.index(c) for c in chunk_ids})
        supported = bool(refs) and supports(answer[start:end], _fragments(citations, refs))
        segments.append({"text": answer[cursor:end], "refs": refs if supported else []})
        cursor = end
    if answer[cursor:]:
        segments.append({"text": answer[cursor:], "refs": []})
    return _reorder(citations, segments)
