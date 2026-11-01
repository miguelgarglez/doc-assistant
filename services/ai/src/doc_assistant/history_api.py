"""Local-only history and review endpoints."""

from __future__ import annotations

import hmac
import ipaddress
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from doc_assistant.history_contract import HistoryRepository


def authorize(request: Request, x_history_token: Annotated[str | None, Header()] = None) -> None:
    try:
        local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    token = getattr(request.app.state, "history_token", "")
    if (
        not local
        or not token
        or not x_history_token
        or not hmac.compare_digest(token, x_history_token)
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def get_store(request: Request) -> HistoryRepository:
    store: HistoryRepository | None = getattr(request.app.state, "history_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="History unavailable")
    return store


router = APIRouter(prefix="/history", dependencies=[Depends(authorize)])
Store = Annotated[HistoryRepository, Depends(get_store)]


class FeedbackInput(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=4000)
    include_context: bool = False


class ReviewInput(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=200)
    expected_answer: str = Field(min_length=1, max_length=4000)
    confirmed_no_sensitive_data: Literal[True]
    confirmed_error: Literal[True]


@router.get("/conversations")
def conversations(
    store: Store,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str = "",
) -> list[dict[str, Any]]:
    return store.conversations_page(limit=limit, offset=offset, search=search)


@router.get("/conversations/{conversation_id}")
def conversation(
    conversation_id: str,
    store: Store,
    limit: int = Query(default=50, ge=1, le=100),
    before_at: str | None = None,
    before_id: str | None = None,
) -> dict[str, Any]:
    if (before_at is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="Both cursor fields are required")
    before = (before_at, before_id) if before_at is not None and before_id is not None else None
    items, cursor = store.list_page(conversation_id, limit=limit, before=before)
    if not items and before is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    from doc_assistant.api import AskResponse

    for item in items:
        if "result" in item:
            try:
                item["result"] = AskResponse.model_validate(item["result"]).model_dump(mode="json")
            except ValidationError:
                del item["result"]
    return {"items": items, "next_cursor": cursor}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request, store: Store) -> dict[str, int]:
    outbox = request.app.state.history_outbox
    deleted = outbox.delete(
        lambda: store.delete_conversation(conversation_id), conversation_id=conversation_id
    )
    return {"deleted": deleted}


@router.delete("/conversations")
def delete_all(request: Request, store: Store) -> dict[str, int]:
    deleted = request.app.state.history_outbox.delete(store.delete_all)
    return {"deleted": deleted}


@router.get("/status")
def status(request: Request) -> dict[str, Any]:
    store = getattr(request.app.state, "history_store", None)
    outbox = getattr(request.app.state, "history_outbox", None)
    return {
        "active": store is not None and outbox is not None,
        "enabled": outbox is not None,
        "initialization_error": getattr(request.app.state, "history_initialization_error", None),
        "retention_days": request.app.state.history_retention_days,
        **(outbox.status() if outbox else {"pending": 0, "failures": []}),
    }


@router.post("/feedback", status_code=201)
def create_feedback(payload: FeedbackInput, store: Store) -> dict[str, str]:
    feedback_id = str(uuid.uuid4())
    saved = store.add_private_feedback(
        feedback_id,
        payload.conversation_id,
        payload.request_id,
        datetime.now(UTC).isoformat(),
        payload.comment,
        include_context=payload.include_context,
    )
    if not saved:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"feedback_id": feedback_id}


@router.get("/feedback")
def feedback(
    store: Store,
    status: Literal["nuevo", "revisado", "descartado", "convertido a caso"] = "nuevo",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    return store.feedback_by_status(status, limit=limit, offset=offset)


@router.get("/feedback/export")
def export_feedback(store: Store) -> StreamingResponse:
    return StreamingResponse(store.export_all_reviewed(), media_type="application/x-ndjson")


@router.post("/feedback/{feedback_id}/review")
def review(feedback_id: str, payload: ReviewInput, store: Store) -> dict[str, bool]:
    if not payload.expected_answer.strip():
        raise HTTPException(status_code=422, detail="Expected answer must not be empty")
    if not store.review_feedback(payload.conversation_id, feedback_id, payload.expected_answer):
        raise HTTPException(status_code=404, detail="Feedback not found")
    return {"reviewed": True}
