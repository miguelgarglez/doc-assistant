"""Rutas y plataforma compartidas por setup.py y dev.py (solo stdlib)."""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IS_WIN = os.name == "nt"
VENDOR = ROOT / "vendor" / "llama"
ARCHIVES = ROOT / "vendor" / "archives"  # tarballs/zip de llama.cpp incluidos en el ZIP de entrega
ASSETS: dict[str, Any] = json.loads((ROOT / "scripts" / "assets.json").read_text(encoding="utf-8"))


ENV_LOCAL = ROOT / ".env.local"
MODELS_DIR_KEY = "DOC_ASSISTANT_MODELS_DIR"


def read_env_local(path: Path = ENV_LOCAL) -> dict[str, str]:
    """Lee KEY=VALUE de .env.local (git-ignorado). Ignora comentarios y líneas vacías."""
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def write_env_local(key: str, value: str, path: Path = ENV_LOCAL) -> None:
    env = read_env_local(path)
    env[key] = value
    path.write_text("".join(f"{k}={v}\n" for k, v in env.items()), encoding="utf-8")


def models_dir(cli: str | None = None, env_local: Path = ENV_LOCAL) -> tuple[Path, str]:
    """Orden: --models-dir > DOC_ASSISTANT_MODELS_DIR > .env.local > ./models. Devuelve (ruta, origen)."""
    if cli:
        return Path(cli).expanduser().resolve(), "--models-dir"
    if os.environ.get(MODELS_DIR_KEY):
        return Path(os.environ[MODELS_DIR_KEY]).expanduser().resolve(), MODELS_DIR_KEY
    local = read_env_local(env_local).get(MODELS_DIR_KEY)
    if local:
        return Path(local).expanduser().resolve(), ".env.local"
    return ROOT / "models", "./models (por defecto)"


def llama_platform() -> tuple[str, str]:
    m = platform.machine().lower()
    arch = "arm64" if m in ("arm64", "aarch64") else "x64"
    if sys.platform == "win32":
        return f"win-cpu-{arch}", "zip"
    if sys.platform == "darwin":
        return f"macos-{arch}", "tar.gz"
    return f"ubuntu-{arch}", "tar.gz"


def llama_exe() -> Path:
    name = "llama-server.exe" if IS_WIN else "llama-server"
    hits = sorted(VENDOR.rglob(name)) if VENDOR.exists() else []
    return hits[0] if hits else VENDOR / name


OCR_URL = "http://127.0.0.1:11434"
OCR_MODEL = "glm-ocr"
OCR_HOWTO = "instala Ollama (https://ollama.com) y ejecuta 'ollama pull glm-ocr'"


OCR_FILES = ("GLM-OCR-Q8_0.gguf", "mmproj-GLM-OCR-Q8_0.gguf")


def ocr_runtime() -> str:
    """'llama' (por defecto: GLM-OCR GGUF del ZIP) u 'ollama' (alternativa documentada)."""
    return os.environ.get("DOC_ASSISTANT_OCR_RUNTIME", "llama")


def ocr_problem(
    runtime: str | None = None, models: Path | None = None, ollama_path: str | None = None
) -> str | None:
    """None si el OCR de facturas está listo; si no, el motivo en una frase (#13)."""
    if (runtime or ocr_runtime()) == "ollama":
        return ollama_problem(ollama_path)
    d = models or models_dir(None)[0]
    missing = [f for f in OCR_FILES if not (d / f).exists()]
    if missing:
        return f"faltan {', '.join(missing)} en {d}; ejecuta 'mise run setup'"
    return None


def ollama_problem(ollama_path: str | None, url: str = OCR_URL, timeout: float = 2) -> str | None:
    """Comprobación del runtime alternativo Ollama + glm-ocr."""
    import urllib.request

    if not ollama_path:
        return f"no encuentro 'ollama' en el PATH; {OCR_HOWTO}"
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=timeout) as r:
            tags = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return f"Ollama no responde en {url}; arráncalo ('ollama serve') o {OCR_HOWTO}"
    names = {str(m.get("name", "")).split(":")[0] for m in tags.get("models", [])}
    if OCR_MODEL not in names:
        return f"Ollama no tiene el modelo '{OCR_MODEL}'; ejecuta 'ollama pull {OCR_MODEL}'"
    return None
