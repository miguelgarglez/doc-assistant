"""Exercise admission, waiting and release without timing model inference."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from doc_assistant import api
from doc_assistant.ask_capacity import AskCapacity


def event(frame: str) -> tuple[str, dict]:
    name, data = frame.strip().split("\n")
    return name.removeprefix("event: "), json.loads(data.removeprefix("data: "))


def test_queue_waits_rejects_overflow_and_releases_on_disconnect(monkeypatch):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.admitted.acquire()
    capacity.running.acquire()
    waiting = api.queued_ask_stream(capacity, Path("unused"), "question")
    name, data = event(next(waiting))
    assert (name, data["status"], data["label"]) == (
        "step",
        "running",
        "Esperando turno para responder",
    )
    overflow = list(api.queued_ask_stream(capacity, Path("unused"), "question"))
    assert event(overflow[0])[1]["code"] == "queue_full"
    waiting.close()
    assert capacity.admitted.acquire(blocking=False)
    capacity.admitted.release()
    capacity.running.release()
    capacity.admitted.release()

    monkeypatch.setattr(api, "ask_stream_events", lambda *_: iter(["finished"]))
    assert list(api.queued_ask_stream(capacity, Path("unused"), "question")) == ["finished"]


def test_queued_request_continues_when_slot_frees(monkeypatch):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.running.acquire()
    monkeypatch.setattr(api, "ask_stream_events", lambda *_: iter(["finished"]))
    stream = api.queued_ask_stream(capacity, Path("unused"), "question")
    assert event(next(stream))[1]["status"] == "running"
    capacity.running.release()
    assert event(next(stream))[1]["status"] == "done"
    assert next(stream) == "finished"
    stream.close()
    assert capacity.running.acquire(blocking=False)
    capacity.running.release()


def test_wait_timeout_is_recoverable_and_releases_admission(monkeypatch):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.running.acquire()
    monkeypatch.setattr(api, "ASK_QUEUE_TIMEOUT_S", 0.01)
    stream = api.queued_ask_stream(capacity, Path("unused"), "question")
    assert event(next(stream))[1]["status"] == "running"
    assert event(next(stream))[1]["code"] == "queue_timeout"
    assert list(stream) == []
    assert capacity.admitted.acquire(blocking=False)
    capacity.admitted.release()
    capacity.running.release()


def test_non_streaming_endpoint_returns_recoverable_overflow(config_path):
    with TestClient(api.create_app(config_path)) as client:
        capacity = client.app.state.ask_capacity
        for _ in range(6):
            assert capacity.admitted.acquire(blocking=False)
        try:
            response = client.post("/ask", json={"question": "Pregunta"})
            assert response.status_code == 503
            assert response.json()["code"] == "queue_full"
        finally:
            for _ in range(6):
                capacity.admitted.release()
