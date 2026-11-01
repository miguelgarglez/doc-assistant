from pathlib import Path
from typing import Literal, Protocol


class Rectangle(Protocol):
    @property
    def x(self) -> float: ...
    @property
    def y(self) -> float: ...
    @property
    def w(self) -> float: ...
    @property
    def h(self) -> float: ...


class PdfPort(Protocol):
    def page_count(
        self, data: bytes
    ) -> tuple[int | None, Literal["pdf_protected", "pdf_unreadable"] | None]: ...

    def locate(self, path: Path, page: int, quote: str) -> list[Rectangle] | None: ...
