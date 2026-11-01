import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from doc_assistant.application.history.outbox import HistoryOutbox
from doc_assistant.history_api import router
from doc_assistant.infra.history.sqlite import HistoryStore


def client_for(tmp_path, host="127.0.0.1"):
    app = FastAPI()
    app.state.history_token = "secret"
    app.state.history_store = HistoryStore(tmp_path / "history.db")
    app.state.history_retention_days = 30
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


def test_history_api_accepts_an_alternative_store(tmp_path):
    client, _ = client_for(tmp_path)

    class AlternativeStore:
        def conversations_page(self, *, limit, offset, search):
            return [{"conversation_id": "alternative", "count": limit, "question": search}]

    client.app.state.history_store = AlternativeStore()
    response = client.get(
        "/history/conversations?limit=2&offset=0&search=demo",
        headers={"x-history-token": "secret"},
    )
    assert response.status_code == 200
    assert response.json() == [{"conversation_id": "alternative", "count": 2, "question": "demo"}]


def test_recent_requests_endpoint_requires_token_and_pages(tmp_path):
    client, store = client_for(tmp_path)
    for request_id in ("a", "b"):
        store.record(request_id, "c", "2026-01-01", {"kind": "answer"})
    assert client.get("/history/requests").status_code == 403
    headers = {"x-history-token": "secret"}
    response = client.get("/history/requests?limit=1&offset=1", headers=headers)
    assert response.status_code == 200
    assert [item["request_id"] for item in response.json()] == ["a"]
    assert client.get("/history/requests?limit=101", headers=headers).status_code == 422


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


def test_decision_exports_only_approved_redactions_and_revokes_on_reopen(tmp_path):
    client, store = client_for(tmp_path)
    headers = {"x-history-token": "secret"}
    store.record("r", "c", "now", {"question": "secret@example.com"})
    assert store.add_private_feedback(
        "f", "c", "r", "now", "secret@example.com", include_context=True
    )
    assert client.get("/history/feedback/f/original").status_code == 403
    assert client.get("/history/feedback/f/original", headers=headers).json()["question"] == (
        "secret@example.com"
    )
    url = "/history/feedback/f/decision"
    decision = {
        "status": "revisado",
        "expected_answer": "respuesta segura",
        "cause": "otro",
        "redacted_comment": "[email]",
        "redacted_context": "[email]",
    }
    assert client.put(url, json=decision, headers=headers).status_code == 422
    assert client.get("/history/feedback/export", headers=headers).text == ""
    decision.update(confirmed_error=True, confirmed_no_sensitive_data=True)
    assert client.put(url, json=decision, headers=headers).status_code == 200
    exported = client.get("/history/feedback/export", headers=headers).text
    assert "secret@example.com" not in exported
    assert json.loads(exported)["redacted_context"] == "[email]"
    assert client.get("/history/feedback/f", headers=headers).json()[
        "export_preview"
    ] == json.loads(exported)
    assert client.get("/history/feedback/counts", headers=headers).json()["revisado"] == 1
    assert client.put(url, json={"status": "descartado"}, headers=headers).status_code == 200
    assert client.get("/history/feedback/export", headers=headers).text == ""
    assert client.put(url, json={"status": "nuevo"}, headers=headers).status_code == 200
    assert client.get("/history/feedback/f", headers=headers).json()["export_preview"] is None


def test_conversation_cursor_and_deletion_cancel_old_stream(tmp_path):
    client, store = client_for(tmp_path)
    client.app.state.history_outbox = HistoryOutbox(store)
    headers = {"x-history-token": "secret"}
    try:
        store.record("r1", "c", "2026-01-01", {"question": "one"})
        store.record("r2", "c", "2026-01-02", {"question": "two"})
        first = client.get("/history/conversations/c?limit=1", headers=headers).json()
        assert first["items"] == [{"question": "two"}]
        cursor = first["next_cursor"]
        second = client.get(
            "/history/conversations/c",
            params={"before_at": cursor[0], "before_id": cursor[1]},
            headers=headers,
        ).json()
        assert second["items"] == [{"question": "one"}]
        outbox = client.app.state.history_outbox
        ticket = outbox.ticket("c")
        assert client.delete("/history/conversations/c", headers=headers).json() == {"deleted": 2}
        outbox.submit("r3", "c", "2026-01-03", {}, ticket=ticket)
        assert outbox.status()["pending"] == 0
        assert store.get("c", "r3") is None
        assert client.get("/history/status", headers=headers).json()["retention_days"] == 30
    finally:
        client.app.state.history_outbox.close()


def test_application_records_stream_and_purges_expired(config_path, tmp_path, monkeypatch):
    import time

    from doc_assistant.api import create_app

    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_TOKEN", "secret")
    store = HistoryStore(tmp_path / "history.db")
    store.record("old", "old", "2000-01-01T00:00:00+00:00", {"question": "expired"})
    with TestClient(create_app(config_path), client=("127.0.0.1", 1234)) as client:
        response = client.post("/ask/stream", json={"question": " ", "conversation_id": "test"})
        assert response.status_code == 200
        assert "event: done" in response.text
        request_id = response.headers["x-request-id"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if store.get("test", request_id) is not None and store.get("old", "old") is None:
                break
            time.sleep(0.01)
        assert store.get("old", "old") is None
        trace = store.get("test", request_id)
        assert trace is not None and trace["request_id"] == request_id
        assert (
            client.get(
                "/history/conversations/test", headers={"x-history-token": "secret"}
            ).status_code
            == 200
        )


def test_history_start_failure_retries_without_changing_stream(config_path, monkeypatch, caplog):
    import time

    from doc_assistant.api import create_app

    original_init = HistoryStore.__init__
    available = False

    def flaky_init(self, path):
        if not available:
            raise OSError("storage offline")
        original_init(self, path)

    monkeypatch.setattr(HistoryStore, "__init__", flaky_init)
    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_TOKEN", "secret")
    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_ENABLED", "1")
    headers = {"x-history-token": "secret"}
    with TestClient(create_app(config_path), client=("127.0.0.1", 1234)) as client:
        status = client.get("/history/status", headers=headers).json()
        assert status["active"] is False
        assert status["enabled"] is True
        assert status["initialization_error"] == "OSError"
        response = client.post("/ask/stream", json={"question": " ", "conversation_id": "c"})
        assert response.status_code == 200
        assert "event: done" in response.text
        request_id = response.headers["x-request-id"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = client.get("/history/status", headers=headers).json()
            if status["failures"]:
                break
            time.sleep(0.01)
        assert status["pending"] == 1
        assert status["failures"][0]["request_id"] == request_id
        assert f"request_id={request_id}" in caplog.text
        available = True
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            status = client.get("/history/status", headers=headers).json()
            if status["active"] and status["pending"] == 0:
                break
            time.sleep(0.01)
        assert status["active"] is True
        assert status["initialization_error"] is None
        assert status["pending"] == 0
        result = client.get("/history/conversations/c", headers=headers).json()
        assert result["items"][0]["request_id"] == request_id


def test_history_can_be_disabled_by_administrator(config_path, monkeypatch):
    from doc_assistant.api import create_app

    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_TOKEN", "secret")
    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_ENABLED", "0")
    with TestClient(create_app(config_path), client=("127.0.0.1", 1234)) as client:
        status = client.get("/history/status", headers={"x-history-token": "secret"}).json()
        assert status["enabled"] is False
        assert status["active"] is False
        assert status["initialization_error"] is None


def test_storage_write_failure_is_reported_without_changing_stream(config_path, monkeypatch):
    import time

    from doc_assistant.api import create_app

    monkeypatch.setenv("DOC_ASSISTANT_HISTORY_TOKEN", "secret")
    with TestClient(create_app(config_path), client=("127.0.0.1", 1234)) as client:

        def fail(*args):
            raise OSError("unavailable")

        monkeypatch.setattr(client.app.state.history_store, "record", fail)
        response = client.post("/ask/stream", json={"question": " "})
        assert "event: done" in response.text
        request_id = response.headers["x-request-id"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = client.get("/history/status", headers={"x-history-token": "secret"}).json()
            if status["failures"]:
                break
            time.sleep(0.01)
        assert status["pending"] == 1
        assert status["failures"][0]["request_id"] == request_id


def test_conversation_validates_stored_results_before_serving(tmp_path):
    client, store = client_for(tmp_path)
    store.record(
        "bad",
        "c",
        "2026-01-01",
        {
            "request_id": "bad",
            "question": "bad",
            "result": {"ok": True, "answer": "bad", "citations": "not a list"},
        },
    )
    store.record(
        "good",
        "c",
        "2026-01-02",
        {
            "request_id": "good",
            "question": "good",
            "result": {"ok": True, "answer": "answer", "citations": [], "reason": ""},
        },
    )
    response = client.get("/history/conversations/c", headers={"x-history-token": "secret"})
    assert response.status_code == 200
    good, bad = response.json()["items"]
    assert good["result"]["answer"] == "answer"
    assert good["result"]["blocks"] == []
    assert "result" not in bad
    assert bad["question"] == "bad"
