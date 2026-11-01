"""Puertos configurables: validación, detección de puerto ocupado y mensaje accionable."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import _common
from _common import PORT_DEFAULTS, PORT_ENV, PortError, busy_message, resolve_ports


def listener() -> tuple[socket.socket, int]:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    return s, int(s.getsockname()[1])


def listener_with_suggestion_range() -> tuple[socket.socket, int]:
    for port in range(8300, 8305):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            s.listen()
            return s, port
        except OSError:
            s.close()
    raise OSError("No test port available in 8300–8304")


def test_defaults_are_the_documented_ports() -> None:
    assert resolve_ports({}) == {
        "llm": 8081,
        "embeddings": 8082,
        "reranker": 8083,
        "ocr": 8084,
        "ai": 8000,
        "web": 3000,
    }


def test_variables_and_overrides_win_over_defaults() -> None:
    env = {"DOC_ASSISTANT_LLM_PORT": "8181", "DOC_ASSISTANT_WEB_PORT": " 3170 "}
    ports = resolve_ports(env, {"ai": 8170})
    assert (ports["llm"], ports["web"], ports["ai"], ports["ocr"]) == (8181, 3170, 8170, 8084)


@pytest.mark.parametrize("bad", ["abc", "0", "70000", "-1", "80.5"])
def test_invalid_port_names_the_variable(bad: str) -> None:
    with pytest.raises(PortError, match="DOC_ASSISTANT_OCR_PORT"):
        resolve_ports({"DOC_ASSISTANT_OCR_PORT": bad})


def test_two_pieces_cannot_share_a_port() -> None:
    with pytest.raises(PortError, match="mismo puerto"):
        resolve_ports({"DOC_ASSISTANT_LLM_PORT": "8082"})


def test_busy_message_says_who_which_variable_and_a_free_port() -> None:
    s, port = listener_with_suggestion_range()
    spare, free = listener()
    spare.close()
    try:
        ports = {**PORT_DEFAULTS, "llm": port, "embeddings": free}
        msg = busy_message(ports, ["llm", "embeddings"])
        assert msg is not None
        assert f"{port} (modelo de lenguaje)" in msg
        assert "DOC_ASSISTANT_LLM_PORT=" in msg
        assert "DOC_ASSISTANT_EMBEDDINGS_PORT" not in msg
        assert "lsof" in msg or "netstat" in msg
        suggested = int(msg.split("DOC_ASSISTANT_LLM_PORT=")[1].split()[0])
        assert suggested != port and not _common.port_busy(suggested)
    finally:
        s.close()


def test_free_ports_give_no_message() -> None:
    s, port = listener()
    s.close()
    assert busy_message({**PORT_DEFAULTS, "llm": port}, ["llm"]) is None


def test_dev_refuses_to_start_on_a_busy_port_and_says_how_to_fix_it() -> None:
    s, port = listener()
    env = {**os.environ, "DOC_ASSISTANT_FAKE_LLAMA": "1", PORT_ENV["ai"]: str(port)}
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "dev.py"), "--no-llm"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            check=False,
        )
    finally:
        s.close()
    assert r.returncode == 2
    assert f"{port} (servicio de IA)" in r.stderr and "DOC_ASSISTANT_AI_PORT=" in r.stderr


def test_dev_rejects_an_invalid_port_before_starting_anything() -> None:
    env = {**os.environ, PORT_ENV["llm"]: "no-es-un-puerto"}
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "dev.py"), "--no-llm"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert r.returncode == 2 and "DOC_ASSISTANT_LLM_PORT" in r.stderr
