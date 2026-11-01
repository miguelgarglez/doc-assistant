from dataclasses import dataclass, field
from typing import Any, Protocol

from doc_assistant.domain.invoices.query_types import Party


@dataclass
class Plan:
    intent: str
    numero: str | None = None
    parte: str | None = None
    campos: list[str] = field(default_factory=list)
    filtros: list[tuple[str, str, Any]] = field(default_factory=list)
    desde: str | None = None
    hasta: str | None = None
    tiene: list[str] = field(default_factory=list)
    sin_anio: bool = False


@dataclass
class Selection:
    numeros: list[str] | None = None
    party: Party | None = None
    rol: str | None = None
    label: str = ""
    selector_fields: list[str] = field(default_factory=list)
    stop: dict[str, Any] | None = None


class InvoiceReader(Protocol):
    def resolve_nif(self, text: str) -> dict[str, Party]: ...
    def resolve_number(self, text: str) -> list[str]: ...
    def resolve_party(self, text: str) -> list[Party]: ...
    def party_tokens(self) -> set[str]: ...
    def rows(self, numeros: list[str]) -> list[dict[str, Any]]: ...
    def matching_numbers(
        self, plan: Plan, sel: Selection, trace: dict[str, Any] | None = None
    ) -> list[str]: ...
