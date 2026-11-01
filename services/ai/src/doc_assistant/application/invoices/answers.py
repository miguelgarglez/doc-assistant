from typing import Any

from doc_assistant.application.invoices.query import followup_question
from doc_assistant.domain.answers.answer_markup import AnswerBuilder, md_escape
from doc_assistant.domain.documents.ids import invoice_doc_id
from doc_assistant.domain.invoices.blocks import build_blocks, follow_ups
from doc_assistant.domain.invoices.fields import display_value


def invoice_citation(numero: str, campo: str, valor: Any) -> dict[str, Any]:
    """The citation of one stored field; its text is the value as the answer shows it."""
    fragment = "" if valor is None else display_value(campo, valor)
    return {
        "chunk_id": f"{numero}:{campo}",
        "quote": fragment,
        "doc": numero or "",
        "doc_id": invoice_doc_id(numero or ""),
        "section": campo or "",
        "pages": [1],
        "fragment": fragment,
    }


def render_plan_answer(
    result: dict[str, Any], citations: list[dict[str, Any]]
) -> tuple[
    str, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]
]:
    """Markdown for a SQL answer (a headline and one cited bullet per invoice or field), plus
    the same rows as blocks and the follow-up questions they allow."""
    out = AnswerBuilder()
    if result.get("headline"):
        out.paragraph(md_escape(result["headline"]))
    by_field = {c["chunk_id"]: c for c in citations}
    for element in result.get("elements") or []:
        refs = [by_field[f"{c['numero']}:{c['campo']}"] for c in element["citations"]]
        out.bullet(md_escape(element["text"]), refs)
    review = result.get("review") or []
    if review:
        out.paragraph(
            "Nota: facturas pendientes de revisión: " + ", ".join(md_escape(n) for n in review)
        )
    answer, _cites, segments = out.build()

    def cite(numero: str, campo: str, valor: Any) -> int:
        citation = by_field.get(f"{numero}:{campo}")
        if citation is None:
            if campo != "numero" or valor != numero:
                raise ValueError("Block value has no selected evidence")
            citation = invoice_citation(numero, campo, numero)
        if citation["quote"] != display_value(campo, valor):
            raise ValueError("Block value differs from selected evidence")
        return out.cite(citation)

    view = result.get("view")
    blocks = build_blocks(view, cite)
    asks = follow_ups(view, lambda fields, numero: followup_question(fields, numero))
    return answer, list(out.citations), segments, blocks, asks


CLARIFY = {
    "aclaracion",
    "factura_ambigua",
    "parte_ambigua",
    "parte_rol_distinto",
    "factura_no_encontrada",
    "parte_no_encontrada",
    "sin_resultados",
}


def format_answer(result: dict[str, Any] | None, raws: list[Any]) -> dict[str, Any] | None:
    if result is None:
        return None
    raw = raws[-1] if raws else None
    citations = [
        invoice_citation(cit.get("numero") or "", cit.get("campo") or "", cit.get("valor"))
        for cit in result.get("citations") or []
    ]
    clarification = result.get("clarification")
    if clarification:
        clarification = {
            **clarification,
            "candidates": [
                {
                    "doc": c["numero"],
                    "doc_id": invoice_doc_id(c["numero"]),
                    **{k: v for k, v in c.items() if k != "numero"},
                }
                for c in clarification["candidates"]
            ],
        }
    if result.get("ok"):
        answer, citations, segments, blocks, asks = render_plan_answer(result, citations)
        return {
            "ok": True,
            "answer": answer,
            "citations": citations,
            "segments": segments,
            "blocks": blocks,
            "follow_ups": asks,
            "inline": "template",
            "reason": result.get("reason") or "sql",
            "suggestions": [],
            "latencies": {},
            "raw": {"plans": raws},
        }
    reason = result.get("reason") or "plan_invalido"
    return {
        "ok": False,
        "answer": (result.get("answer") if reason in CLARIFY and result.get("answer") else None)
        or "No dispongo de esa información en los documentos",
        "citations": [],
        "reason": f"invoice:{reason}",
        "suggestions": [],
        "clarification": clarification,
        "latencies": {},
        "raw": {"plans": raws, "last": raw},
    }
