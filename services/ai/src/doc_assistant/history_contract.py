"""Operations required of a history store by the local API and worker."""

from collections.abc import Iterator
from typing import Any, Protocol

from doc_assistant.history_outbox import HistoryWriter


class HistoryRepository(HistoryWriter, Protocol):
    def requests_page(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]: ...

    def conversations_page(
        self, *, owner: str = "local", limit: int = 50, offset: int = 0, search: str = ""
    ) -> list[dict[str, Any]]: ...

    def list_page(
        self, conversation_id: str, *, limit: int = 50, before: tuple[str, str] | None = None
    ) -> tuple[list[dict[str, Any]], tuple[str, str] | None]: ...

    def delete_conversation(self, conversation_id: str, *, owner: str = "local") -> int: ...

    def delete_all(self, *, owner: str = "local") -> int: ...

    def add_private_feedback(
        self,
        feedback_id: str,
        conversation_id: str,
        request_id: str,
        created_at: str,
        comment: str | None,
        *,
        include_context: bool = False,
    ) -> bool: ...

    def feedback_by_status(
        self, status: str, *, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]: ...

    def export_all_reviewed(self) -> Iterator[str]: ...

    def review_feedback(self, conversation_id: str, feedback_id: str, answer: str) -> bool: ...

    def purge_before(self, cutoff: str) -> tuple[int, int]: ...
