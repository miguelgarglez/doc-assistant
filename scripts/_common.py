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
