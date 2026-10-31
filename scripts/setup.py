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
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from _common import (
    ARCHIVES,
    ASSETS,
    IS_WIN,
    MODELS_DIR_KEY,
    ROOT,
    VENDOR,
    llama_exe,
    llama_platform,
    models_dir,
    ocr_problem,
    write_env_local,
)

VCREDIST = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
STATUS_DLL_NOT_FOUND = 0xC0000135


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, expected: str, size: int | None = None) -> None:
    """Descarga con reanudación (.part + Range) y verificación SHA256."""
    tmp = dest.with_name(dest.name + ".part")
    start = tmp.stat().st_size if tmp.exists() else 0
    if start and size is not None and start >= size:
        if start == size and sha256(tmp) == expected:
            tmp.replace(dest)
            return
        tmp.replace(tmp.with_name(tmp.name + ".bad"))
        start = 0
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-"} if start else {})
    print(
        f"[setup] descargando {url}" + (f" (reanudo desde {start / 1e9:.2f} GB)" if start else ""),
        flush=True,
    )
    try:
        response = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code != 416 or not start:
            raise
        if sha256(tmp) == expected:
            tmp.replace(dest)
            return
        tmp.replace(tmp.with_name(tmp.name + ".bad"))
        response = urllib.request.urlopen(urllib.request.Request(url), timeout=60)
        start = 0
    with response as r:
        mode = "ab" if start and r.status == 206 else "wb"
        with tmp.open(mode) as f:
            shutil.copyfileobj(r, f, 1 << 20)
    got = sha256(tmp)
    if got != expected:
        raise SystemExit(
            f"[setup] SHA256 no coincide para {dest.name}: {got} != {expected}. El .part queda para revisar."
        )
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
    cfg = ASSETS["llama_cpp"]
    marker = VENDOR / "VERSION"
    if llama_exe().exists() and marker.is_file() and marker.read_text().strip() == cfg["tag"]:
        print(f"[setup] llama-server ya presente: {llama_exe()}")
        return
    plat, ext = llama_platform()
    url = cfg["url"].format(tag=cfg["tag"], plat=plat, ext=ext)
    VENDOR.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=VENDOR.parent) as td:
        local = ARCHIVES / url.rsplit("/", 1)[1]
        if local.exists() and sha256(local) == cfg["sha256"][plat]:
            print(f"[setup] llama-server desde el paquete: {local.name} (SHA256 OK, sin descarga)")
            archive = local
        else:
            archive = Path(td) / f"llama.{ext}"
            download(url, archive, cfg["sha256"][plat])
        staging = Path(td) / "llama"
        staging.mkdir()
        if ext == "zip":
            with zipfile.ZipFile(archive) as z:
                z.extractall(staging)  # zip de Windows: plano (exe + dll)
        else:
            with tarfile.open(archive) as t:
                t.extractall(staging, filter="data")
        executable = "llama-server.exe" if IS_WIN else "llama-server"
        if not any(staging.rglob(executable)):
            raise SystemExit("[setup] el archivo no contiene llama-server")
        (staging / "VERSION").write_text(str(cfg["tag"]) + "\n")
        backup = Path(td) / "previous"
        if VENDOR.exists():
            VENDOR.rename(backup)
        try:
            staging.rename(VENDOR)
        except Exception:
            if backup.exists():
                backup.rename(VENDOR)
            raise


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


def plan_models(d: Path, verify: bool) -> list[dict[str, object]]:
    """Modelos que faltan (o no cuadran). Lo existente con tamaño correcto no se descarga."""
    missing: list[dict[str, object]] = []
    for m in ASSETS["models"]:
        path = d / m["file"]
        if path.exists() and path.stat().st_size == m["size"]:
            if verify and sha256(path) != m["sha256"]:
                raise SystemExit(
                    f"[setup] {path} tiene el tamaño correcto pero el SHA256 no coincide. Revísalo."
                )
            print(
                f"[setup] OK {m['file']} ({'SHA256 verificado' if verify else 'tamaño correcto'})"
            )
        else:
            missing.append(m)
    return missing


def install_models(d: Path, verify: bool, yes: bool) -> None:
    d.mkdir(parents=True, exist_ok=True)
    missing = plan_models(d, verify)
    if not missing:
        print(f"[setup] usando modelos de {d}: no hay nada que descargar")
        return
    total = sum(int(str(m["size"])) for m in missing) / 1e9
    print(
        f"[setup] descargaré {', '.join(str(m['file']) for m in missing)} ({total:.1f} GB) en {d}"
    )
    if total > 1 and not yes:
        if not sys.stdin.isatty():
            raise SystemExit(
                "[setup] más de 1 GB y sin terminal: repite con --yes o indica --models-dir"
            )
        if input("[setup] ¿Continuar? [s/N] ").strip().lower() not in {
            "s",
            "si",
            "sí",
            "y",
            "yes",
        }:
            raise SystemExit("[setup] cancelado. Usa --models-dir <ruta> si ya tienes los modelos.")
    for m in missing:
        download(str(m["url"]), d / str(m["file"]), str(m["sha256"]), int(str(m["size"])))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-model", action="store_true", help="no descargar GGUF (CI)")
    ap.add_argument("--check-llama", action="store_true", help="solo comprobar llama-server")
    ap.add_argument("--models-dir", help="carpeta con los GGUF (se guarda en .env.local)")
    ap.add_argument(
        "--verify",
        action="store_true",
        help="verificar SHA256 de los modelos existentes (lento)",
    )
    ap.add_argument("--yes", action="store_true", help="no preguntar antes de descargar (CI)")
    a = ap.parse_args()
    d, origin = models_dir(a.models_dir)
    print(f"[setup] carpeta de modelos: {d}  (origen: {origin})", flush=True)
    if a.check_llama:
        check_llama()
        return 0
    run([tool("uv"), "sync", "--frozen"], ROOT / "services" / "ai")
    run([tool("pnpm"), "install", "--frozen-lockfile"], ROOT)
    run([tool("pnpm"), "--filter", "web", "build"], ROOT)
    install_llama()
    check_llama()
    if not a.no_model:
        install_models(d, a.verify, a.yes)
        write_env_local(MODELS_DIR_KEY, str(d))
        print(f"[setup] guardado {MODELS_DIR_KEY}={d} en .env.local (lo usará 'mise run start')")
    why = ocr_problem(shutil.which("ollama"))
    if why:
        print(f"[setup] AVISO: Facturas no funcionará hasta que {why}")
    else:
        print("[setup] OCR de facturas listo (Ollama + glm-ocr)")
    print("[setup] listo. Arranca con: mise run start")
    return 0


if __name__ == "__main__":
    sys.exit(main())
