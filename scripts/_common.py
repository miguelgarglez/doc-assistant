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


def models_dir() -> Path:
    """DOC_ASSISTANT_MODELS_DIR permite reutilizar modelos ya descargados (sin redescargar)."""
    env = os.environ.get("DOC_ASSISTANT_MODELS_DIR")
    return Path(env).expanduser() if env else ROOT / "models"


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
