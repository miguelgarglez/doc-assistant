"""Arranque único y multiplataforma: llama-server x3 + servicio IA + web.

Solo stdlib, sin shell ni .cmd: `sys.executable -m uvicorn` y `node .../next`.
Puertos comprobados conectando (no reservando), health checks en orden,
cierre en dos fases (amable, 5 s, forzado del árbol) y `atexit` como red.
Variables: DOC_ASSISTANT_MODELS_DIR, DOC_ASSISTANT_LLAMA_SERVER, DOC_ASSISTANT_FAKE_LLAMA=1 (CI).
Puertos (por defecto 8081-8084, 8000 y 3000): DOC_ASSISTANT_LLM_PORT, _EMBEDDINGS_PORT,
_RERANKER_PORT, _OCR_PORT, _AI_PORT y _WEB_PORT; config/config.yaml lee las mismas.
"""

from __future__ import annotations

import argparse
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from _common import (
    IS_WIN,
    LOOPBACK,
    OCR_FILES,
    PORT_ENV,
    ROOT,
    PortError,
    busy_message,
    llama_exe,
    models_dir,
    ocr_problem,
    ocr_runtime,
    port_busy,
    resolve_ports,
)

GRACE_S = 5.0


@dataclass
class Proc:
    name: str
    cmd: list[str]
    port: int
    health: str
    cwd: Path = ROOT
    env: dict[str, str] = field(default_factory=dict)
    timeout_s: float = 90
    reuse_if_running: bool = False  # servicio del sistema (Ollama): se reutiliza, no se cierra
    popen: subprocess.Popen[bytes] | None = None


def llama(name: str, port: int, model: str, *extra: str) -> Proc:
    health = f"http://{LOOPBACK}:{port}/health"
    if os.environ.get("DOC_ASSISTANT_FAKE_LLAMA") == "1":
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "fake_llama.py"),
            "--port",
            str(port),
        ]
        return Proc(name, cmd, port, health)
    exe = os.environ.get("DOC_ASSISTANT_LLAMA_SERVER") or (
        str(llama_exe()) if llama_exe().exists() else shutil.which("llama-server")
    )
    if not exe:
        raise SystemExit("[dev] no encuentro llama-server. Ejecuta 'mise run setup'.")
    path = models_dir(os.environ.get("_DOC_ASSISTANT_CLI_MODELS_DIR"))[0] / model
    if not path.exists():
        raise SystemExit(
            f"[dev] falta el modelo {path}. Ejecuta 'mise run setup' o define DOC_ASSISTANT_MODELS_DIR."
        )
    cmd = [exe, "-m", str(path), "--host", LOOPBACK, "--port", str(port), *extra]
    return Proc(name, cmd, port, health, timeout_s=180)


def plan(dev: bool, ports: dict[str, int], with_llm: bool) -> list[Proc]:
    ai_port, web_port = ports["ai"], ports["web"]
    node = shutil.which("node")
    if node is None:
        raise SystemExit("[dev] no encuentro node. ¿Has ejecutado 'mise install'?")
    next_bin = ROOT / "apps" / "web" / "node_modules" / "next" / "dist" / "bin" / "next"
    web = [
        node,
        str(next_bin),
        "dev" if dev else "start",
        "-H",
        LOOPBACK,
        "-p",
        str(web_port),
    ]
    api = [
        sys.executable,
        "-m",
        "uvicorn",
        "doc_assistant.api:app",
        "--host",
        LOOPBACK,
        "--port",
        str(ai_port),
    ]
    models = (
        [
            llama(
                "llm",
                ports["llm"],
                os.environ.get("DOC_ASSISTANT_LLM_MODEL", "Qwen3.5-4B-Q4_K_M.gguf"),
                "-c",
                "8192",
                "-np",
                "2",
                "--reasoning-budget",  # sin "pensar": respuesta directa (como en el slice)
                "0",
            ),
            llama(
                "embeddings",
                ports["embeddings"],
                "bge-m3-Q8_0.gguf",
                "--embeddings",
                "--pooling",
                "cls",
            ),
            llama("reranker", ports["reranker"], "bge-reranker-v2-m3-Q8_0.gguf", "--reranking"),
        ]
        if with_llm
        else []
    )
    fake = os.environ.get("DOC_ASSISTANT_FAKE_LLAMA") == "1"
    ollama = shutil.which("ollama")
    ocr: list[Proc] = []
    if with_llm and not fake and ocr_runtime() == "ollama" and ollama:
        # alternativa documentada: Ollama del sistema (se reutiliza si ya corre)
        ocr = [
            Proc(
                "ocr",
                [ollama, "serve"],
                11434,
                f"http://{LOOPBACK}:11434/api/version",
                reuse_if_running=True,
            )
        ]
    elif with_llm and not fake and ocr_runtime() == "llama":
        # por defecto: GLM-OCR GGUF del ZIP. Ajustes medidos (16 GB junto al LLM, sin OOM):
        # contexto 8192, flash-attn y la imagen limitada a 1600 tokens.
        mmproj = models_dir(os.environ.get("_DOC_ASSISTANT_CLI_MODELS_DIR"))[0] / OCR_FILES[1]
        ocr = [
            llama(
                "ocr",
                ports["ocr"],
                OCR_FILES[0],
                "--mmproj",
                str(mmproj),
                "-c",
                "8192",
                "--flash-attn",
                "on",
                "--image-max-tokens",
                "1600",
                "--temp",
                "0",
            )
        ]
    return [
        *models,
        *ocr,
        Proc(
            "ai",
            api,
            ai_port,
            f"http://{LOOPBACK}:{ai_port}/health",
            ROOT / "services" / "ai",
            {PORT_ENV[name]: str(port) for name, port in ports.items()},
        ),
        Proc(
            "web",
            web,
            web_port,
            f"http://{LOOPBACK}:{web_port}/",
            ROOT / "apps" / "web",
            {"AI_SERVICE_URL": f"http://{LOOPBACK}:{ai_port}"},
        ),
    ]


def wait_healthy(p: Proc) -> None:
    deadline = time.monotonic() + p.timeout_s
    while time.monotonic() < deadline:
        if p.popen is not None and p.popen.poll() is not None:
            raise RuntimeError(f"{p.name} terminó con código {p.popen.returncode}")
        try:
            with urllib.request.urlopen(p.health, timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{p.name} no respondió en {p.health} tras {p.timeout_s:.0f}s")


STARTED: list[Proc] = []


def start(p: Proc) -> None:
    if IS_WIN:
        flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        p.popen = subprocess.Popen(
            p.cmd, cwd=p.cwd, env={**os.environ, **p.env}, creationflags=flags
        )
    else:
        p.popen = subprocess.Popen(
            p.cmd, cwd=p.cwd, env={**os.environ, **p.env}, start_new_session=True
        )
    STARTED.append(p)
    print(f"[dev] {p.name} pid={p.popen.pid} puerto={p.port}", flush=True)


def _alive() -> list[subprocess.Popen[bytes]]:
    return [p.popen for p in reversed(STARTED) if p.popen is not None and p.popen.poll() is None]


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _groups() -> list[int]:
    """Grupos iniciados (POSIX: pgid = pid del líder). Vivos aunque el líder ya haya muerto."""
    return [p.popen.pid for p in reversed(STARTED) if p.popen is not None]


def stop_all() -> None:
    # uv/mise reenvían la señal y el terminal la manda al grupo: ignorar las repetidas
    # mientras cerramos evita un KeyboardInterrupt a mitad de la parada.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_IGN)
    if IS_WIN:
        _stop_windows()
        return
    live = [g for g in _groups() if _group_alive(g)]
    if not live:
        return
    for g in live:  # fase 1: amable, a todo el grupo (también si el líder murió: #14)
        try:
            os.killpg(g, signal.SIGTERM)
        except OSError:
            pass
    deadline = time.monotonic() + GRACE_S
    while time.monotonic() < deadline and any(_group_alive(g) for g in live):
        for pp in _alive():
            pp.poll()
        time.sleep(0.1)
    for g in live:  # fase 2: forzado
        if _group_alive(g):
            try:
                os.killpg(g, signal.SIGKILL)
            except OSError:
                pass
    for p in STARTED:
        if p.popen is not None:
            try:
                p.popen.wait(5)
            except subprocess.TimeoutExpired:
                pass
    print("[dev] todos los procesos cerrados", flush=True)


def _stop_windows() -> None:
    if not _alive():
        return
    for pp in _alive():
        try:
            pp.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        except OSError:
            pass
    deadline = time.monotonic() + GRACE_S
    for pp in _alive():
        try:
            pp.wait(max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for pp in _alive():  # árbol completo (si el padre murió, taskkill /T no ve a los hijos)
        subprocess.run(
            ["taskkill", "/PID", str(pp.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    print("[dev] todos los procesos cerrados", flush=True)


def _interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dev", action="store_true", help="next dev en vez de next start")
    ap.add_argument("--no-llm", action="store_true", help="sin llama-server (solo UI/contrato)")
    ap.add_argument("--ai-port", type=int, help="puerto del servicio IA (DOC_ASSISTANT_AI_PORT)")
    ap.add_argument("--web-port", type=int, help="puerto de la web (DOC_ASSISTANT_WEB_PORT)")
    ap.add_argument(
        "--models-dir",
        help="carpeta con los GGUF (si no: DOC_ASSISTANT_MODELS_DIR, .env.local, ./models)",
    )
    a = ap.parse_args()
    if a.models_dir:
        os.environ["_DOC_ASSISTANT_CLI_MODELS_DIR"] = a.models_dir
    if not a.no_llm and os.environ.get("DOC_ASSISTANT_FAKE_LLAMA") != "1":
        d, origin = models_dir(a.models_dir)
        print(f"[dev] modelos: {d}  (origen: {origin})", flush=True)

    # Explícito: aunque SIGINT llegue ignorado (proceso en segundo plano) o llegue SIGTERM/SIGBREAK.
    signal.signal(signal.SIGINT, _interrupt)
    signal.signal(signal.SIGTERM, _interrupt)
    if IS_WIN:
        signal.signal(signal.SIGBREAK, _interrupt)  # type: ignore[attr-defined]
    atexit.register(stop_all)

    cli = {k: v for k, v in (("ai", a.ai_port), ("web", a.web_port)) if v is not None}
    try:
        ports = resolve_ports(overrides=cli)
    except PortError as e:
        print(f"[dev] ERROR: {e}", file=sys.stderr)
        return 2
    procs = plan(a.dev, ports, with_llm=not a.no_llm)
    with_ocr = not a.no_llm and os.environ.get("DOC_ASSISTANT_FAKE_LLAMA") != "1"
    reused = [p for p in procs if p.reuse_if_running and port_busy(p.port)]
    procs = [p for p in procs if p not in reused]
    for p in reused:
        print(
            f"[dev] {p.name}: ya en marcha en {p.port}, se reutiliza (no se cerrará)",
            flush=True,
        )
    in_use = [name for name, port in ports.items() if any(p.port == port for p in procs)]
    problem = busy_message(ports, in_use)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    if not a.dev and not (ROOT / "apps" / "web" / ".next" / "BUILD_ID").exists():
        print(
            "[dev] ERROR: falta el build de la web. Ejecuta 'mise run build'.",
            file=sys.stderr,
        )
        return 2
    try:
        for p in procs:
            start(p)
            wait_healthy(p)
            print(f"[dev] {p.name} OK", flush=True)
        if with_ocr:
            why = ocr_problem(ollama_path=shutil.which("ollama"))
            if why:
                print(f"[dev] AVISO: Facturas NO disponible: {why}", flush=True)
        print(
            f"[dev] Listo: http://{LOOPBACK}:{ports['web']}  (Ctrl-C para salir)",
            flush=True,
        )
        while not any(p.popen is not None and p.popen.poll() is not None for p in STARTED):
            time.sleep(0.5)
        dead = next(p for p in STARTED if p.popen is not None and p.popen.poll() is not None)
        print(f"[dev] ERROR: {dead.name} se ha detenido; cierro el resto", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except RuntimeError as e:
        print(f"[dev] ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        stop_all()


if __name__ == "__main__":
    sys.exit(main())
