import pytest

from doc_assistant.domain.answers.answer_markup import md_escape, section_label, split_heading


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("4. Mantenimiento", "4\\. Mantenimiento"),
        ("2.1. Cableado", "2.1. Cableado"),
        ("- vale", "\\- vale"),
        ("doc_final*v2", "doc\\_final\\*v2"),
        ("<documento> [x]", "\\<documento\\> \\[x\\]"),
        ("a | b", "a \\| b"),
    ],
)
def test_md_escape(raw: str, escaped: str) -> None:
    assert md_escape(raw) == escaped


def test_section_label_never_starts_like_a_list() -> None:
    assert split_heading("2.1. Cálculo de distancia") == ("2.1", "Cálculo de distancia")
    assert section_label("2.1. Cálculo de distancia") == "§2.1 Cálculo de distancia"
    assert section_label("4. Mantenimiento") == "§4 Mantenimiento"
    assert section_label("Resumen") == "Resumen"
