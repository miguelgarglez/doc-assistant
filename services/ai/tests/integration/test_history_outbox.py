import threading
import time

from doc_assistant.application.history.outbox import HistoryOutbox


def test_delete_invalidates_retry_and_stream_started_before_deletion(tmp_path):
    from doc_assistant.infra.history.sqlite import HistoryStore

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


def test_delete_waits_for_active_write_then_removes_it(tmp_path):
    from doc_assistant.infra.history.sqlite import HistoryStore

    store = HistoryStore(tmp_path / "history.db")
    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    class SlowStore:
        def record(self, request_id, conversation_id, created_at, trace):
            entered.set()
            assert release.wait(2)
            store.record(request_id, conversation_id, created_at, trace)

    outbox = HistoryOutbox(SlowStore())
    result = []
    worker = None
    try:
        ticket = outbox.ticket("c")
        outbox.submit("r", "c", "now", {"question": "old"}, ticket=ticket)
        assert entered.wait(1)

        def delete():
            result.append(
                outbox.delete(lambda: store.delete_conversation("c"), conversation_id="c")
            )
            finished.set()

        worker = threading.Thread(target=delete)
        worker.start()
        assert not finished.wait(0.05)
        release.set()
        assert finished.wait(2)
        assert result == [1]
        assert store.get("c", "r") is None
        outbox.submit("late", "c", "now", {"question": "late"}, ticket=ticket)
        assert store.get("c", "late") is None
    finally:
        release.set()
        if worker:
            worker.join(timeout=2)
        outbox.close()
