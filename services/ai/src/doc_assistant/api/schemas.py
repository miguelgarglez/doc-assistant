from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=200)


class Citation(BaseModel):
    chunk_id: str
    quote: str
    doc: str
    doc_id: str
    section: str
    pages: list[int]
    fragment: str


class Suggestion(BaseModel):
    """A real, nearby source shown when the question cannot be answered."""

    doc: str
    doc_id: str
    section: str
    heading: str | None = None
    pages: list[int]


class Segment(BaseModel):
    """A piece of the answer and the citations that support it.

    `refs` are positions in `citations`. The `text` of all segments concatenates to the answer.
    """

    text: str
    refs: list[int]


class ClarificationCandidate(BaseModel):
    """An invoice the question may refer to. Every field comes from the stored invoice."""

    doc: str
    doc_id: str
    emisor: str | None = None
    cliente: str | None = None
    fecha: str | None = None
    total: str | None = None
    question: str


class Clarification(BaseModel):
    """The question is ambiguous: the user picks one of the real candidates.

    `question` of the chosen candidate is the original question with that invoice named.
    `total` counts every matching invoice; `candidates` holds at most the first five.
    """

    prompt: str
    detail: str | None = None
    total: int
    candidates: list[ClarificationCandidate]


CellKind = Literal["text", "date", "amount", "percent", "id"]


class Cell(BaseModel):
    """One stored value as the answer shows it. `text` is None when the invoice has no such value.

    `cite` is the position in `citations` of the citation that carries the same stored value.
    """

    text: str | None = None
    kind: CellKind
    cite: int | None = None


class KeyDatum(Cell):
    field: str
    label: str


class KeyDataBlock(BaseModel):
    """The data of one invoice, each with its citation."""

    type: Literal["key_data"] = "key_data"
    title: str
    doc_id: str
    items: list[KeyDatum]
    note: str | None = None


class TableColumn(BaseModel):
    key: str
    label: str
    kind: CellKind


class TableRow(BaseModel):
    """`cells` follow `columns`. `question` asks for the data of this row's invoice."""

    doc_id: str
    question: str
    cells: list[Cell]


class TableSummary(BaseModel):
    """Calculated total, with the citation positions of every operand."""

    operation: Literal["sum"] = "sum"
    refs: list[int]
    label: str
    text: str
    kind: Literal["amount"] = "amount"


class TableBlock(BaseModel):
    """Invoices as rows. The first column is the invoice number."""

    type: Literal["table"] = "table"
    title: str | None = None
    columns: list[TableColumn]
    rows: list[TableRow]
    summary: TableSummary | None = None
    note: str | None = None


Block = Annotated[KeyDataBlock | TableBlock, Field(discriminator="type")]


class FollowUp(BaseModel):
    """A question the service can answer from what it found: a field of the same invoice, or a nearby section."""

    label: str
    question: str


class AskResponse(BaseModel):
    ok: bool
    answer: str
    citations: list[Citation]
    segments: list[Segment] = Field(default_factory=list)
    blocks_version: Literal[1] = 1
    blocks: list[Block] = Field(default_factory=list)
    follow_ups: list[FollowUp] = Field(default_factory=list)
    inline: Literal["model", "rules", "template", "none"] = "none"
    reason: str
    suggestions: list[Suggestion] = Field(default_factory=list)
    clarification: Clarification | None = None


StepId = Literal["route", "meta", "invoices", "retrieve", "rerank", "generate", "verify"]


class StepEvent(BaseModel):
    event: Literal["step"] = "step"
    id: StepId
    status: Literal["running", "done"]
    label: str
    data: dict[str, Any] = Field(default_factory=dict)
    elapsed_s: float | None = None


class TokenEvent(BaseModel):
    event: Literal["token"] = "token"
    text: str


class CitationsEvent(BaseModel):
    event: Literal["citations"] = "citations"
    citations: list[Citation]


class BlocksEvent(BaseModel):
    event: Literal["blocks"] = "blocks"
    blocks_version: Literal[1] = 1
    blocks: list[Block]
    follow_ups: list[FollowUp] = Field(default_factory=list)


class RefusalEvent(BaseModel):
    event: Literal["refusal"] = "refusal"
    answer: str
    reason: str
    retract: bool
    suggestions: list[Suggestion] = Field(default_factory=list)


class ClarificationEvent(BaseModel):
    event: Literal["clarification"] = "clarification"
    reason: str
    clarification: Clarification


class DoneEvent(AskResponse):
    event: Literal["done"] = "done"
    timings: dict[str, float]
    request_id: str


class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = Annotated[
    StepEvent
    | TokenEvent
    | CitationsEvent
    | BlocksEvent
    | RefusalEvent
    | ClarificationEvent
    | DoneEvent
    | ErrorEvent,
    Field(discriminator="event"),
]
