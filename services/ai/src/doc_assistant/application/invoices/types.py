from dataclasses import dataclass, field
from typing import Any

from doc_assistant.domain.invoices.query_types import Party


@dataclass
class Plan:
    intent: str
    numero: str | None = None
    parte: str | None = None
    campos: list[str] = field(default_factory=list)
    filtros: list[tuple[str, str, Any]] = field(default_factory=list)  # (col, op, typed value)
    desde: str | None = None
    hasta: str | None = None
    tiene: list[str] = field(default_factory=list)
    sin_anio: bool = False  # dates compare on MM-DD only


@dataclass
class Selection:
    numeros: list[str] | None = None  # None = no restriction
    party: Party | None = None
    rol: str | None = None
    label: str = ""
    selector_fields: list[str] = field(default_factory=list)
    stop: dict[str, Any] | None = None  # clarification or refusal decided while resolving
