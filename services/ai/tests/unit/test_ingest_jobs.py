import threading
import time

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
