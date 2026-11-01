"""Local-only history and review endpoints."""

from __future__ import annotations

import hmac
import ipaddress
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from doc_assistant.history import HistoryStore


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


def get_store(request: Request) -> HistoryStore:
    store = getattr(request.app.state, "history_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="History unavailable")
    return store


router = APIRouter(prefix="/history", dependencies=[Depends(authorize)])
Store = Annotated[HistoryStore, Depends(get_store)]


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
) -> list[dict]:
    return store.conversations_page(limit=limit, offset=offset, search=search)


@router.get("/conversations/{conversation_id}")
def conversation(
    conversation_id: str,
    store: Store,
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    items, cursor = store.list_page(conversation_id, limit=limit)
    if not items:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"items": items, "next_cursor": cursor}


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
) -> list[dict]:
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
