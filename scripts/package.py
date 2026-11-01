"""Empaqueta la entrega en un ZIP64 autocontenido y lo prueba en limpio.

Contenido: ficheros versionados (git ls-files: código, docs, evidence), modelos
finales en models/ con SHA256SUMS, binarios llama.cpp fijados para macOS arm64,
Linux x64 y Windows x64 en vendor/archives/, y NOTICE. Nunca entra lo ignorado
por git (.venv, node_modules, _trash, _agents, kit, .env.local, data).
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import (
    ARCHIVES,
    ASSETS,
    ROOT,
    PortError,
    busy_message,
    models_dir,
    port_busy,
    resolve_ports,
)
from setup import download, sha256

PLATFORMS = {"macos-arm64": "tar.gz", "ubuntu-x64": "tar.gz", "win-cpu-x64": "zip"}
FORBIDDEN = (
    "_trash/",
    "_agents/",
    ".audit/",
    "node_modules/",
    ".venv/",
    "kit/",
    ".env.local",
    "data/",
    "AGENTS.md",
    "HANDOFF.md",
    "CHECKPOINT.md",
)
STORED = (".gguf", ".zip", ".tar.gz", ".png", ".pdf")


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode()
    files = [f for f in out.split("\0") if f and (ROOT / f).is_file()]
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        print(
            "[package] AVISO: hay cambios sin commit; el ZIP refleja el árbol de trabajo de los ficheros versionados"
        )
    bad = [f for f in files if any(f.startswith(x) or f"/{x}" in f for x in FORBIDDEN)]
    if bad:
        raise SystemExit(f"[package] ficheros prohibidos versionados: {bad[:5]}")
    return files


def llama_archives() -> list[Path]:
    cfg = ASSETS["llama_cpp"]
    ARCHIVES.mkdir(parents=True, exist_ok=True)
    out = []
    for plat, ext in PLATFORMS.items():
        url = cfg["url"].format(tag=cfg["tag"], plat=plat, ext=ext)
        dest = ARCHIVES / url.rsplit("/", 1)[1]
        if not (dest.exists() and sha256(dest) == cfg["sha256"][plat]):
            download(url, dest, cfg["sha256"][plat])
        out.append(dest)
    return out


def model_files(src: Path) -> list[Path]:
    out = []
    for m in ASSETS["models"]:
        p = src / str(m["file"])
        if not p.exists() or p.stat().st_size != int(m["size"]):
            raise SystemExit(f"[package] falta o no cuadra {p}; ejecuta mise run setup")
        if sha256(p) != m["sha256"]:
            raise SystemExit(f"[package] SHA256 no coincide: {p}")
        out.append(p)
    return out


def build(zip_path: Path, prefix: str, src_models: Path, with_models: bool) -> None:
    files = tracked_files()
    archives = llama_archives()
    models = model_files(src_models) if with_models else []
    sums = "".join(f"{m['sha256']}  {m['file']}\n" for m in ASSETS["models"]) if models else ""
    t0 = time.time()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for f in files:
            comp = zipfile.ZIP_STORED if f.endswith(STORED) else zipfile.ZIP_DEFLATED
            z.write(ROOT / f, f"{prefix}/{f}", compress_type=comp)
        for a in archives:
            z.write(
                a,
                f"{prefix}/vendor/archives/{a.name}",
                compress_type=zipfile.ZIP_STORED,
            )
        for m in models:
            z.write(m, f"{prefix}/models/{m.name}", compress_type=zipfile.ZIP_STORED)
        if sums:
            z.writestr(f"{prefix}/models/SHA256SUMS", sums)
    size = zip_path.stat().st_size
    print(
        f"[package] {zip_path} · {size / 1e9:.2f} GB · {len(files)} ficheros + "
        f"{len(archives)} binarios + {len(models)} modelos · {time.time() - t0:.0f} s"
    )


def http_ok(url: str, data: bytes | None = None, ctype: str = "application/json") -> str:
    req = urllib.request.Request(url, data=data, headers={"content-type": ctype})
    with urllib.request.urlopen(req, timeout=120) as r:
        body: bytes = r.read()
        return body.decode()


def smoke(zip_path: Path, prefix: str, fake: bool) -> None:
    """Descomprime en limpio, setup + start + pregunta. Falla si setup descarga algo."""
    try:
        ports = resolve_ports()
    except PortError as e:
        raise SystemExit(f"[smoke] {e}") from e
    checked = [n for n in ports if not (fake and n == "ocr")]
    problem = busy_message(ports, checked, tool="smoke")
    if problem:
        raise SystemExit(problem + "\n[smoke] la prueba en limpio necesita esos puertos libres.")
    web = f"http://127.0.0.1:{ports['web']}/api"
    td = Path(tempfile.mkdtemp(prefix="doc-assistant-unpack-"))
    t0 = time.time()
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(td)
    root = td / prefix
    drop = {"DOC_ASSISTANT_MODELS_DIR", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
    env = {k: v for k, v in os.environ.items() if k not in drop}
    uvrun = ["uv", "run", "--project", "services/ai", "python"]
    setup_cmd = [*uvrun, "scripts/setup.py", "--yes"] + (["--no-model"] if fake else [])
    r = subprocess.run(setup_cmd, check=False, cwd=root, env=env, capture_output=True, text=True)
    log = r.stdout + r.stderr
    (td / "setup.log").write_text(log)
    if r.returncode != 0:
        raise SystemExit(f"[smoke] setup falló:\n{log[-2000:]}")
    if "[setup] descargando" in log:
        raise SystemExit("[smoke] setup descargó algo (debería usar lo empaquetado)")
    print(f"[smoke] setup OK sin descargas de modelos/binarios ({time.time() - t0:.0f} s)")
    if fake:
        env["DOC_ASSISTANT_FAKE_LLAMA"] = "1"
    kw: dict[str, object] = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}  # type: ignore[attr-defined]
        if sys.platform == "win32"
        else {"start_new_session": True}
    )
    out = open(td / "start.log", "w")  # noqa: SIM115
    p = subprocess.Popen(
        [*uvrun, "scripts/dev.py"], cwd=root, env=env, stdout=out, stderr=out, **kw
    )  # type: ignore[call-overload]
    try:
        deadline = time.time() + 300
        while time.time() < deadline:
            try:
                http_ok(f"{web}/health")
                break
            except OSError:
                if p.poll() is not None:
                    raise SystemExit(
                        f"[smoke] start terminó: {(td / 'start.log').read_text()[-1500:]}"
                    )
                time.sleep(2)

        def upload(url: str, f: Path, ctype: str) -> str:
            boundary = "docassistsmoke"
            body = (
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                    f'filename="{f.name}"\r\nContent-Type: {ctype}\r\n\r\n'
                ).encode()
                + f.read_bytes()
                + f"\r\n--{boundary}--\r\n".encode()
            )
            return http_ok(url, body, f"multipart/form-data; boundary={boundary}")

        pdf = root / "evidence/fixtures/docs/sensor-demo.pdf"
        print(
            "[smoke] /documents:",
            upload(f"{web}/documents", pdf, "application/pdf")[:120],
        )
        q = '{"question":"¿Qué alcance tiene el sensor?"}'.encode()
        t1 = time.time()
        ans = http_ok(f"{web}/ask", q)
        print(f"[smoke] /ask ({time.time() - t1:.0f} s):", ans[:300])
        if not fake and '"citations":[]' in ans.replace(" ", ""):
            raise SystemExit("[smoke] /ask sin cita")
        if not fake:
            inv = root / "evidence/fixtures/invoices/factura_001.png"
            t1 = time.time()
            r_inv = upload(f"{web}/invoices/upload", inv, "image/png")
            print(f"[smoke] /invoices/upload ({time.time() - t1:.0f} s):", r_inv[:300])
    finally:
        if sys.platform == "win32":
            p.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
        else:
            os.killpg(p.pid, signal.SIGINT)  # todo el grupo: uv no reenvía SIGINT sin TTY
        p.wait(timeout=30)
        out.close()
    if "Traceback" in (td / "start.log").read_text():
        raise SystemExit(f"[smoke] hubo un Traceback en start.log ({td})")
    time.sleep(2)
    still = [ports[n] for n in checked if port_busy(ports[n])]
    if still:
        raise SystemExit(f"[smoke] puertos sin liberar tras parar: {still}")
    print(f"[smoke] puertos {', '.join(str(ports[n]) for n in checked)} liberados")
    print(f"[smoke] OK en {time.time() - t0:.0f} s · logs en {td}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", default="miguel_garcia_tooling")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "_dist")
    ap.add_argument(
        "--models-dir",
        type=Path,
        help="origen de los modelos (por defecto, la resolución de setup)",
    )
    ap.add_argument(
        "--no-models", action="store_true", help="ZIP ligero sin modelos (solo pruebas)"
    )
    ap.add_argument("--smoke", choices=["none", "fake", "real"], default="fake")
    a = ap.parse_args()
    if shutil.which("git") is None:
        raise SystemExit("[package] necesito git")
    src, origin = models_dir(str(a.models_dir) if a.models_dir else None)
    print(f"[package] modelos desde {src} ({origin})")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = a.out_dir / f"{a.name}.zip"
    build(zip_path, a.name, src, not a.no_models)
    if a.smoke != "none":
        smoke(zip_path, a.name, a.smoke == "fake")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
