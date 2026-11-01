import asyncio
import logging
import os
import secrets
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from doc_assistant.application.ask.capacity import AskCapacity
from doc_assistant.application.ingest.jobs import IngestJobs
from doc_assistant.config import load_config


def lifespan_for(config_path: Path) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.config = load_config(config_path)
        app.state.jobs = IngestJobs()
        app.state.ask_capacity = AskCapacity()
        app.state.config.db.parent.mkdir(parents=True, exist_ok=True)
        app.state.history_token = os.environ.get(
            "DOC_ASSISTANT_HISTORY_TOKEN"
        ) or secrets.token_urlsafe(32)
        app.state.history_retention_days = max(
            1, int(os.environ.get("DOC_ASSISTANT_HISTORY_RETENTION_DAYS", "30"))
        )
        app.state.history_store = None
        app.state.history_outbox = None
        app.state.history_initialization_error = None
        purge_task = None
        if os.environ.get("DOC_ASSISTANT_HISTORY_ENABLED", "1") != "0":
            from doc_assistant.application.history.outbox import HistoryOutbox
            from doc_assistant.history import HistoryStore
            from doc_assistant.history_contract import HistoryRepository

            store_lock = threading.Lock()

            def open_history() -> HistoryRepository:
                with store_lock:
                    store: HistoryRepository | None = app.state.history_store
                    if store is not None:
                        return store
                    try:
                        store = HistoryStore(app.state.config.db.parent / "history.db")
                        cutoff = (
                            datetime.now(UTC) - timedelta(days=app.state.history_retention_days)
                        ).isoformat()
                        store.purge_before(cutoff)
                    except Exception as exc:
                        app.state.history_initialization_error = type(exc).__name__
                        raise
                    app.state.history_store = store
                    app.state.history_initialization_error = None
                    return store

            class RecoveringWriter:
                def record(
                    self,
                    request_id: str,
                    conversation_id: str,
                    created_at: str,
                    trace: dict[str, Any],
                ) -> None:
                    open_history().record(request_id, conversation_id, created_at, trace)

            app.state.history_outbox = HistoryOutbox(RecoveringWriter())
            try:
                await asyncio.to_thread(open_history)
            except Exception:
                logging.getLogger(__name__).exception("History initialization failed")

            async def purge() -> None:
                while True:
                    try:
                        store = await asyncio.to_thread(open_history)
                        cutoff = (
                            datetime.now(UTC) - timedelta(days=app.state.history_retention_days)
                        ).isoformat()
                        await asyncio.to_thread(store.purge_before, cutoff)
                    except Exception:
                        logging.getLogger(__name__).exception("History retention failed")
                        await asyncio.sleep(5)
                    else:
                        await asyncio.sleep(3600)

            purge_task = asyncio.create_task(purge())
        try:
            yield
        finally:
            if purge_task is not None:
                purge_task.cancel()
                try:
                    await purge_task
                except asyncio.CancelledError:
                    pass
            if app.state.history_outbox is not None:
                app.state.history_outbox.close()

    return lifespan
