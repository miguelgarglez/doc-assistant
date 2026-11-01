import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_assistant.history import HistoryStore
from doc_assistant.history_api import router


def client_for(tmp_path, host="127.0.0.1"):
    app = FastAPI()
    app.state.history_token = "secret"
    app.state.history_store = HistoryStore(tmp_path / "history.db")
    app.include_router(router)
    return TestClient(app, client=(host, 1234)), app.state.history_store


def test_history_requires_token_and_actual_loopback_peer(tmp_path):
    client, _ = client_for(tmp_path)
    assert client.get("/history/conversations").status_code == 403
    assert (
        client.get("/history/conversations", headers={"x-history-token": "wrong"}).status_code
        == 403
    )
    assert (
        client.get("/history/conversations", headers={"x-history-token": "secret"}).status_code
        == 200
    )
    remote, _ = client_for(tmp_path, host="192.0.2.4")
    assert (
        remote.get(
            "/history/conversations",
            headers={"x-history-token": "secret", "x-forwarded-for": "127.0.0.1"},
        ).status_code
        == 403
    )


def test_review_export_requires_human_confirmations_and_excludes_pending(tmp_path):
    client, store = client_for(tmp_path)
    headers = {"x-history-token": "secret"}
    store.record("r", "c", "2026-01-01", {"question": "invoice 123"})
    payload = {"request_id": "r", "conversation_id": "c", "comment": "wrong"}
    first = client.post("/history/feedback", json=payload, headers=headers)
    assert first.status_code == 201
    feedback_id = first.json()["feedback_id"]
    client.post("/history/feedback", json=payload, headers=headers)
    assert client.get("/history/feedback/export", headers=headers).text == ""
    review = {"conversation_id": "c", "expected_answer": "correct"}
    assert (
        client.post(
            f"/history/feedback/{feedback_id}/review", json=review, headers=headers
        ).status_code
        == 422
    )
    review.update(confirmed_error=True, confirmed_no_sensitive_data=True)
    assert (
        client.post(
            f"/history/feedback/{feedback_id}/review", json=review, headers=headers
        ).status_code
        == 200
    )
    exported = [
        json.loads(line)
        for line in client.get("/history/feedback/export", headers=headers).text.splitlines()
    ]
    assert len(exported) == 1
    assert exported[0]["feedback_id"] == feedback_id
    assert exported[0]["trace"] == {"request_id": "r", "conversation_id": "c"}
    assert len(client.get("/history/feedback", headers=headers).json()) == 1
