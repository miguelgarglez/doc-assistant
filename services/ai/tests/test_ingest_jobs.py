"""Progress of uploads: stages in order, late followers, errors and the HTTP contract."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from doubles import FakeEmbedder
from fastapi.testclient import TestClient

from doc_assistant.api import create_app
from doc_assistant.application.ingest.jobs import IngestJobs

JOB = "job-0123456789"


def stages(jobs: IngestJobs, job: str) -> list[str]:
    return [s.stage for s in jobs.follow(job, appear_timeout=0.2) if s is not None]


def test_follow_yields_each_stage_in_order_then_stops() -> None:
    jobs = IngestJobs()
    seen: list[str] = []
    follower = threading.Thread(target=lambda: seen.extend(stages(jobs, JOB)))
    follower.start()
    for stage in ("received", "reading", "indexing"):
        jobs.update(JOB, stage)  # type: ignore[arg-type]
        time.sleep(0.05)
    jobs.done(JOB, kind="document")
    follower.join(5)
    assert seen[0] in ("received", "reading") and seen[-1] == "done"
    assert seen == sorted(set(seen), key=seen.index)


def test_late_follower_gets_the_final_state_and_terminal_states_stick() -> None:
    jobs = IngestJobs()
    jobs.update(JOB, "received")
    jobs.fail(JOB, "invalid_file", "File is not a PDF")
    jobs.update(JOB, "indexing")
    assert stages(jobs, JOB) == ["error"]
    state = jobs.get(JOB)
    assert state is not None and state.detail == {
        "code": "invalid_file",
        "message": "File is not a PDF",
    }


def test_unknown_job_ends_after_the_wait_and_idle_jobs_send_keepalives() -> None:
    jobs = IngestJobs()
    unknown = list(jobs.follow("nobody-1234", appear_timeout=0.05, keepalive=0.01))
    assert all(item is None for item in unknown)
    jobs.update(JOB, "reading")
    beat = list(jobs.follow(JOB, idle_timeout=0.05, keepalive=0.01))
    assert beat[0] is not None and beat[0].stage == "reading" and None in beat[1:]


def test_jobs_are_bounded() -> None:
    jobs = IngestJobs()
    for i in range(300):
        jobs.update(f"job-{i:08d}", "received")
    assert jobs.get("job-00000000") is None and jobs.get("job-00000299") is not None


def events(body: str) -> list[dict[str, Any]]:
    out = []
    for block in body.strip().split("\n\n"):
        if block.startswith(":"):
            continue
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        assert lines["event"] == "stage"
        out.append(json.loads(lines["data"]))
    return out


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "doc_assistant.bootstrap.build_adapters",
        lambda cfg: (FakeEmbedder(dim=8), None, None),
    )


def test_document_upload_publishes_stages_and_a_result(
    config_path: Path, synthetic_pdf: Path, fakes: None
) -> None:
    with TestClient(create_app(config_path)) as client:
        sent = client.post(
            f"/documents?job={JOB}",
            files={"file": ("manual.pdf", synthetic_pdf.read_bytes(), "application/pdf")},
        )
        assert sent.status_code == 200
        got = events(client.get(f"/ingest/jobs/{JOB}/events").text)
    assert [e["stage"] for e in got] == ["done"]
    assert got[0]["detail"]["created"] is True and got[0]["detail"]["n_chunks"] > 0
    assert got[0]["detail"]["doc_id"] == sent.json()["doc_id"]


def test_duplicate_upload_reports_created_false(
    config_path: Path, synthetic_pdf: Path, fakes: None
) -> None:
    payload = synthetic_pdf.read_bytes()
    with TestClient(create_app(config_path)) as client:
        for job in ("job-first-0001", "job-again-0002"):
            client.post(
                f"/documents?job={job}", files={"file": ("m.pdf", payload, "application/pdf")}
            )
        again = events(client.get("/ingest/jobs/job-again-0002/events").text)
    assert again[-1]["detail"]["created"] is False


def test_rejected_upload_publishes_the_error(config_path: Path, fakes: None) -> None:
    with TestClient(create_app(config_path)) as client:
        bad = client.post(
            f"/documents?job={JOB}", files={"file": ("nota.txt", b"hola", "text/plain")}
        )
        got = events(client.get(f"/ingest/jobs/{JOB}/events").text)
    assert bad.status_code == 400
    assert got[-1]["stage"] == "error" and got[-1]["detail"]["code"] == "invalid_file"


def test_upload_without_job_still_works_and_bad_ids_are_rejected(
    config_path: Path, synthetic_pdf: Path, fakes: None
) -> None:
    with TestClient(create_app(config_path)) as client:
        ok = client.post(
            "/documents", files={"file": ("m.pdf", synthetic_pdf.read_bytes(), "application/pdf")}
        )
        bad = client.post(
            "/documents?job=../x", files={"file": ("m.pdf", b"%PDF", "application/pdf")}
        )
        assert client.get("/ingest/jobs/ab/events").status_code == 422
    assert ok.status_code == 200 and bad.status_code == 422


def test_document_stages_are_reported_while_it_is_processed(
    config_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str] = []

    class Slow(FakeEmbedder):
        def embed(self, texts: list[str]) -> list[list[float]]:
            time.sleep(0.2)
            return super().embed(texts)

    monkeypatch.setattr(
        "doc_assistant.bootstrap.build_adapters", lambda cfg: (Slow(dim=8), None, None)
    )
    app = create_app(config_path)
    with TestClient(app) as client:
        upload = threading.Thread(
            target=lambda: client.post(
                f"/documents?job={JOB}",
                files={"file": ("m.pdf", synthetic_pdf.read_bytes(), "application/pdf")},
            )
        )
        upload.start()
        for state in app.state.jobs.follow(JOB, appear_timeout=5):
            if state is not None:
                seen.append(state.stage)
        upload.join(10)
    assert seen[0] == "received" and "indexing" in seen and seen[-1] == "done"
    assert seen == sorted(seen, key={"received": 0, "reading": 1, "indexing": 2, "done": 3}.get)


def test_ingest_batches_embeddings_and_reports_progress(config_path: Path, tmp_path: Path) -> None:
    from reportlab.pdfgen.canvas import Canvas

    from doc_assistant.ingest import ingest_pdfs

    pdf = tmp_path / "many.pdf"
    canvas = Canvas(str(pdf))
    canvas.drawString(50, 800, "Manual")
    for n in range(40):
        y = 780 - (n % 20) * 35
        if n == 20:
            canvas.showPage()
        canvas.drawString(50, y, f"{n + 1}. Apartado")
        canvas.drawString(50, y - 15, f"Contenido del apartado {n + 1}.")
    canvas.save()
    sizes = []
    events = []

    class Recording(FakeEmbedder):
        def embed(self, texts: list[str]) -> list[list[float]]:
            sizes.append(len(texts))
            return super().embed(texts)

    result = ingest_pdfs(
        config_path,
        pdf,
        embedder=Recording(dim=8),
        progress=lambda stage, **detail: events.append((stage, detail)),
    )
    assert result["n_chunks"] == 40
    assert sizes == [32, 8]
    assert ("reading", {"current": 2, "total": 2}) in events
    assert ("indexing", {"current": 40, "total": 40}) in events
