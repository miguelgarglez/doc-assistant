from typing import Any

import pytest

from doc_assistant.application.ask.pipeline import place_inline_citations
from doc_assistant.domain.answers.inline import (
    assign_by_rules,
    overlap,
    split_sentences,
    supports,
    validate_model_segments,
)

CABLE = "[d · t · 2.1. Cableado] Usar cable de 2.5 mm2 para la alimentación principal."

STOP = "[d · t · 3. Parada] La parada se completa en menos de 500 ms."

CITATIONS = [
    {"chunk_id": "c1", "quote": "cable de 2.5 mm2", "fragment": CABLE},
    {"chunk_id": "c2", "quote": "menos de 500 ms", "fragment": STOP},
]

ANSWER = "Usar cable de 2.5 mm2 para alimentar. La parada tarda menos de 500 ms."


IDS = ["c1", "c2"]


def raw(*pairs: tuple[str, list[str]]) -> list[dict[str, Any]]:
    return [{"text": t, "chunk_ids": ids} for t, ids in pairs]


def test_split_sentences_tiles_the_answer() -> None:
    for text in (ANSWER, "Uno.\n\n- dos\n- tres", "sin punto", "4.5 m y 3 m. Fin."):
        assert "".join(split_sentences(text)) == text


def test_overlap_and_support() -> None:
    assert overlap("Usar cable de 2.5 mm2", CABLE) == 1.0
    assert supports("Usar cable de 2.5 mm2 para alimentar.", [CABLE])
    assert not supports("Usar cable de 4 mm2 para alimentar.", [CABLE])
    assert not supports("La batería dura diez años.", [CABLE])


def test_rules_put_each_marker_on_its_own_sentence() -> None:
    citations, segments = assign_by_rules(ANSWER, CITATIONS)
    assert "".join(s["text"] for s in segments) == ANSWER
    assert [citations[s["refs"][0]]["chunk_id"] for s in segments] == ["c1", "c2"]


def test_rules_leave_unsupported_sentences_without_marker() -> None:
    answer = ANSWER + " La garantía dura diez años."
    _, segments = assign_by_rules(answer, CITATIONS)
    assert [bool(s["refs"]) for s in segments] == [True, True, False]


def test_rules_renumber_by_first_use() -> None:
    reversed_answer = "La parada tarda menos de 500 ms. Usar cable de 2.5 mm2 para alimentar."
    citations, segments = assign_by_rules(reversed_answer, CITATIONS)
    assert [c["chunk_id"] for c in citations] == ["c2", "c1"]
    assert [s["refs"] for s in segments] == [[0], [1]]


def test_citations_no_sentence_uses_are_dropped() -> None:
    extra = {
        "chunk_id": "c3",
        "quote": "filtros",
        "fragment": "[d · t · 4. Mantenimiento] Revisar los filtros cada 6 meses.",
    }
    ordered, segments = assign_by_rules(
        "La parada tarda menos de 500 ms.", [CITATIONS[0], extra, CITATIONS[1]]
    )
    assert [c["chunk_id"] for c in ordered] == ["c2"]
    assert segments == [{"text": "La parada tarda menos de 500 ms.", "refs": [0]}]


def test_when_nothing_is_supported_every_citation_stays_for_the_end_list() -> None:
    ordered, segments = assign_by_rules("Respuesta sin ninguna relación.", CITATIONS)
    assert [c["chunk_id"] for c in ordered] == ["c1", "c2"]
    assert all(segment["refs"] == [] for segment in segments)


def test_model_segments_are_accepted_when_supported() -> None:
    model = raw(
        ("Usar cable de 2.5 mm2 para alimentar.", ["c1"]),
        ("La parada tarda menos de 500 ms.", ["c2"]),
    )
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    _, segments = placed
    assert "".join(s["text"] for s in segments) == ANSWER
    assert [s["refs"] for s in segments] == [[0], [1]]


@pytest.mark.parametrize(
    "model",
    [
        None,
        [],
        "texto",
        [{"text": "No está en la respuesta.", "chunk_ids": ["c1"]}],
        [{"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": ["inventado"]}],
        [{"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": "c1"}],
        [
            {"text": "La parada tarda menos de 500 ms.", "chunk_ids": ["c2"]},
            {"text": "Usar cable de 2.5 mm2 para alimentar.", "chunk_ids": ["c1"]},
        ],
    ],
)
def test_malformed_model_segments_are_rejected(model: Any) -> None:
    assert validate_model_segments(ANSWER, model, CITATIONS, IDS) is None


def test_segment_whose_fragment_does_not_support_it_loses_its_marker() -> None:
    model = raw(
        ("Usar cable de 2.5 mm2 para alimentar.", ["c2"]),
        ("La parada tarda menos de 500 ms.", ["c2"]),
    )
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    assert [s["refs"] for s in placed[1]] == [[], [0]]


def test_uncovered_text_stays_in_a_segment_without_marker() -> None:
    model = raw(("La parada tarda menos de 500 ms.", ["c2"]))
    placed = validate_model_segments(ANSWER, model, CITATIONS, IDS)
    assert placed is not None
    assert "".join(s["text"] for s in placed[1]) == ANSWER
    assert placed[1][0]["refs"] == []


def test_place_inline_degrades_from_model_to_rules_to_none() -> None:
    good = raw(("Usar cable de 2.5 mm2 para alimentar.", ["c1"]))
    assert place_inline_citations("model", ANSWER, CITATIONS, good)[2] == "model"
    assert place_inline_citations("model", ANSWER, CITATIONS, None)[2] == "rules"
    assert place_inline_citations("rules", ANSWER, CITATIONS, good)[2] == "rules"
    assert place_inline_citations("off", ANSWER, CITATIONS, good) == (CITATIONS, [], "none")
    unrelated = "Nada que ver con los fragmentos de este documento."
    assert place_inline_citations("rules", unrelated, CITATIONS, None) == (CITATIONS, [], "none")
