import os
import signal
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dev


@pytest.mark.skipif(sys.platform == "win32", reason="grupos de proceso POSIX")
def test_stop_all_kills_orphan_child_of_dead_leader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pidfile = tmp_path / "child.pid"
    # el líder lanza un hijo que ignora SIGTERM y termina enseguida (#14)
    cmd = [
        "sh",
        "-c",
        f"sh -c 'trap \"\" TERM; echo $$ > {pidfile}; while :; do sleep 0.1; done' & sleep 0.3",
    ]
    p = dev.Proc("orphan", cmd, 0, "http://127.0.0.1:1/")
    monkeypatch.setattr(dev, "STARTED", [])
    monkeypatch.setattr(dev, "GRACE_S", 0.5)
    dev.start(p)
    assert p.popen is not None
    p.popen.wait(5)  # el líder ya ha muerto
    for _ in range(50):
        if pidfile.exists() and pidfile.read_text().strip():
            break
        time.sleep(0.1)
    child = int(pidfile.read_text())
    os.kill(child, 0)  # el hijo sigue vivo
    old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        dev.stop_all()
    finally:
        for s, h in old.items():
            signal.signal(s, h)
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
