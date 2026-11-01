import json

from doc_assistant.domain.answers.partial_json import FieldStreamer


def test_field_streamer_decodes_answer_in_any_split() -> None:
    obj = {
        "citations": [{"quote": '"answer": no'}],
        "answer": 'A "b" \u00e9\nc',
        "answerable": True,
    }
    text = json.dumps(obj)
    for size in (1, 2, 5, 64):
        f = FieldStreamer("answer")
        assert (
            "".join(f.feed(text[i : i + size]) for i in range(0, len(text), size)) == obj["answer"]
        )
    assert FieldStreamer("answer").feed('{"answerable":false,"answer":null}') == ""


def test_scope_sentence_is_verbatim_first_sentence() -> None:
    from doc_assistant.application.answers.meta import _scope_sentence

    body = "Este documento define la instalación. Incluye cableado."
    chunk = {"heading": "1. Alcance", "body": body, "text": f"[d · t · 1. Alcance] {body}"}
    other = {"heading": "2. Cableado", "body": "x.", "text": "x."}
    assert _scope_sentence([other, chunk]) == (chunk, "Este documento define la instalación.")
    assert _scope_sentence([other]) is None
