"""Exercise admission, waiting and release without timing model inference."""

import json
from functools import partial
from pathlib import Path

from fastapi.testclient import TestClient

from doc_assistant import bootstrap as api
from doc_assistant.api import streaming as stream_module
from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.bootstrap import ask_events

queued_ask_stream = partial(stream_module.queued_ask_stream, ask_events_fn=ask_events)


def event(frame: str) -> tuple[str, dict]:
    name, data = frame.strip().split("\n")
    return name.removeprefix("event: "), json.loads(data.removeprefix("data: "))


def test_queue_waits_rejects_overflow_and_releases_on_disconnect(monkeypatch):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.admitted.acquire()
    capacity.running.acquire()
    interrupted_trace: dict = {}
    waiting = queued_ask_stream(capacity, Path("unused"), "question", trace=interrupted_trace)
    name, data = event(next(waiting))
    assert (name, data["status"], data["label"]) == (
        "step",
        "running",
        "Esperando turno para responder",
    )
    overflow_trace: dict = {}
    overflow = list(queued_ask_stream(capacity, Path("unused"), "question", trace=overflow_trace))
    assert event(overflow[0])[1]["code"] == "queue_full"
    assert overflow_trace["request_id"]
    assert overflow_trace["transport_status"] == "error"
    assert overflow_trace["status"] == "error"
    assert overflow_trace["error_code"] == "queue_full"
    assert overflow_trace["transport_error_code"] == "queue_full"
    waiting.close()
    assert interrupted_trace["status"] == "interrupted"
    assert interrupted_trace["queue_steps"][0]["label"] == data["label"]
    assert interrupted_trace["finished_at"] >= interrupted_trace["started_at"]
    assert capacity.admitted.acquire(blocking=False)
    capacity.admitted.release()
    capacity.running.release()
    capacity.admitted.release()

    monkeypatch.setattr(
        stream_module, "ask_stream_events", lambda *_, **_kwargs: iter(["finished"])
    )
    assert list(queued_ask_stream(capacity, Path("unused"), "question")) == ["finished"]


def test_queued_request_continues_when_slot_frees(monkeypatch):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.running.acquire()
    monkeypatch.setattr(
        stream_module, "ask_stream_events", lambda *_, **_kwargs: iter(["finished"])
    )
    stream = queued_ask_stream(capacity, Path("unused"), "question")
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
    monkeypatch.setattr(stream_module, "ASK_QUEUE_TIMEOUT_S", 0.01)
    trace: dict = {}
    stream = queued_ask_stream(capacity, Path("unused"), "question", trace=trace)
    assert event(next(stream))[1]["status"] == "running"
    assert event(next(stream))[1]["code"] == "queue_timeout"
    assert trace["status"] == "error"
    assert trace["error_code"] == "queue_timeout"
    assert trace["transport_error_code"] == "queue_timeout"
    assert trace["queue_steps"][0]["status"] == "running"
    assert trace["finished_at"] >= trace["started_at"]
    assert list(stream) == []
    assert capacity.admitted.acquire(blocking=False)
    capacity.admitted.release()
    capacity.running.release()


def test_admitted_request_preserves_pipeline_trace(config_path):
    capacity = AskCapacity(running=1, waiting=1)
    trace: dict = {}
    frames = list(queued_ask_stream(capacity, config_path, "", "request-123", trace=trace))
    assert event(frames[-1])[0] == "done"
    assert trace["request_id"] == event(frames[-1])[1]["request_id"] == "request-123"
    assert trace["status"] == "completed"
    assert trace["transport_status"] == "completed"
    assert trace["result"]["reason"] == "pregunta_vacia"
    assert trace["queue_wait_s"] >= 0


def test_close_after_done_releases_capacity_and_keeps_completion(config_path):
    capacity = AskCapacity(running=1, waiting=0)
    trace: dict = {}
    stream = queued_ask_stream(capacity, config_path, "", trace=trace)
    assert event(next(stream))[0] == "refusal"
    assert event(next(stream))[0] == "done"
    stream.close()
    assert trace["transport_status"] == "completed"
    assert trace["status"] == "completed"
    assert trace["finished_at"] >= trace["started_at"]
    assert capacity.admitted.acquire(blocking=False)
    assert capacity.running.acquire(blocking=False)
    capacity.running.release()
    capacity.admitted.release()


def test_waiting_steps_survive_completed_pipeline(config_path):
    capacity = AskCapacity(running=1, waiting=1)
    capacity.running.acquire()
    trace: dict = {}
    stream = queued_ask_stream(capacity, config_path, "", trace=trace)
    first = event(next(stream))[1]
    capacity.running.release()
    second = event(next(stream))[1]
    list(stream)
    assert trace["queue_steps"] == [first, second]
    assert trace["status"] == "completed"
    assert trace["started_at"] <= trace["finished_at"]
    assert trace["elapsed_s"] >= trace["pipeline_elapsed_s"]
    assert trace["elapsed_s"] >= trace["queue_wait_s"]


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
