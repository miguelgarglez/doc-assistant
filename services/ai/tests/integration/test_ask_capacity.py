"""Exercise admission, waiting and release without timing model inference."""

import json
from functools import partial

from fastapi.testclient import TestClient

from doc_assistant import bootstrap as api
from doc_assistant.api import streaming as stream_module
from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.bootstrap import ask_events

queued_ask_stream = partial(stream_module.queued_ask_stream, ask_events_fn=ask_events)


def event(frame: str) -> tuple[str, dict]:
    name, data = frame.strip().split("\n")
    return name.removeprefix("event: "), json.loads(data.removeprefix("data: "))


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
