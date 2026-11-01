import threading
import time

from doc_assistant.history_outbox import HistoryOutbox


def test_outbox_retries_failure_without_blocking_submit(caplog):
    attempted = threading.Event()
    completed = threading.Event()

    class FlakyStore:
        calls = 0

        def record(self, request_id, conversation_id, created_at, trace):
            self.calls += 1
            attempted.set()
            if self.calls == 1:
                raise OSError("unavailable")
            assert (request_id, conversation_id, created_at, trace) == (
                "r1",
                "c1",
                "now",
                {"question": "test"},
            )
            completed.set()

    store = FlakyStore()
    outbox = HistoryOutbox(store, retry_base=0.05)
    try:
        outbox.submit("r1", "c1", "now", {"question": "test"})
        assert attempted.wait(1)
        assert completed.wait(2)
        deadline = time.monotonic() + 1
        while outbox.status()["pending"] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert outbox.status() == {
            "pending": 0,
            "failures": [{"request_id": "r1", "error": "OSError"}],
        }
        assert "request_id=r1" in caplog.text
    finally:
        outbox.close()


def test_delete_invalidates_retry_and_stream_started_before_deletion(tmp_path):
    from doc_assistant.history import HistoryStore

    real = HistoryStore(tmp_path / "history.db")
    failed = threading.Event()

    class UnavailableStore:
        def record(self, *args):
            failed.set()
            raise OSError("unavailable")

    outbox = HistoryOutbox(UnavailableStore(), retry_base=0.05)
    try:
        ticket = outbox.ticket("c")
        outbox.submit("r1", "c", "now", {"question": "old"}, ticket=ticket)
        assert failed.wait(1)
        outbox.delete(lambda: real.delete_conversation("c"), conversation_id="c")
        outbox.submit("r2", "c", "now", {"question": "old stream"}, ticket=ticket)
        deadline = time.monotonic() + 1
        while outbox.status()["pending"] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert outbox.status()["pending"] == 0
        assert real.get("c", "r1") is None
        assert real.get("c", "r2") is None
        assert outbox.ticket("c") != ticket
    finally:
        outbox.close()
