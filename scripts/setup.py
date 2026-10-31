"""Prepara el entorno: dependencias, llama-server fijado (con SHA256) y modelos GGUF.

Uso: python scripts/setup.py [--no-model] [--check-llama]
Sin API de GitHub: URL directa del asset del tag fijado en assets.json.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from _common import ASSETS, IS_WIN, ROOT, VENDOR, llama_exe, llama_platform, models_dir

VCREDIST = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
STATUS_DLL_NOT_FOUND = 0xC0000135


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, expected: str) -> None:
    print(f"[setup] descargando {url}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=60) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    got = sha256(tmp)
    if got != expected:
        raise SystemExit(f"[setup] SHA256 no coincide para {dest.name}: {got} != {expected}")
    tmp.replace(dest)


def tool(name: str) -> str:
    """Ruta absoluta (en Windows resuelve pnpm.cmd sin shell=True)."""
    path = shutil.which(name)
    if path is None:
        raise SystemExit(
            f"[setup] no encuentro '{name}' en el PATH. ¿Has ejecutado 'mise install'?"
        )
    return path


def run(cmd: list[str], cwd: Path) -> None:
    print(f"[setup] {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def install_llama() -> None:
    if llama_exe().exists():
        print(f"[setup] llama-server ya presente: {llama_exe()}")
        return
    cfg = ASSETS["llama_cpp"]
    plat, ext = llama_platform()
    url = cfg["url"].format(tag=cfg["tag"], plat=plat, ext=ext)
    VENDOR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / f"llama.{ext}"
        download(url, archive, cfg["sha256"][plat])
        if ext == "zip":
            with zipfile.ZipFile(archive) as z:
                z.extractall(VENDOR)  # zip de Windows: plano (exe + dll)
        else:
            with tarfile.open(archive) as t:
                t.extractall(VENDOR, filter="data")


def check_llama() -> None:
    exe = llama_exe()
    if not exe.exists():
        raise SystemExit(f"[setup] no encuentro {exe}")
    r = subprocess.run([str(exe), "--version"], capture_output=True, text=True, check=False)
    if IS_WIN and (r.returncode & 0xFFFFFFFF) == STATUS_DLL_NOT_FOUND:
        raise SystemExit(
            f"[setup] falta el runtime de Visual C++ (vcruntime140.dll). Instálalo: {VCREDIST}"
        )
    if r.returncode != 0:
        raise SystemExit(
            f"[setup] llama-server --version falló ({r.returncode}): {r.stderr.strip()[:300]}"
        )
    print(f"[setup] llama-server OK: {(r.stdout or r.stderr).strip().splitlines()[-1]}")


def install_models() -> None:
    d = models_dir()
    d.mkdir(parents=True, exist_ok=True)
    for m in ASSETS["models"]:
        path = d / m["file"]
        if path.exists() and path.stat().st_size == m["size"]:
            print(
                f"[setup] modelo presente: {path} (tamaño correcto; sha256 verificado al descargar)"
            )
            continue
        download(m["url"], path, m["sha256"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-model", action="store_true", help="no descargar GGUF (CI)")
    ap.add_argument("--check-llama", action="store_true", help="solo comprobar llama-server")
    a = ap.parse_args()
    if a.check_llama:
        check_llama()
        return 0
    run([tool("uv"), "sync", "--frozen"], ROOT / "services" / "ai")
    run([tool("pnpm"), "install", "--frozen-lockfile"], ROOT)
    run([tool("pnpm"), "--filter", "web", "build"], ROOT)
    install_llama()
    check_llama()
    if not a.no_model:
        install_models()
    print("[setup] listo. Arranca con: mise run start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
