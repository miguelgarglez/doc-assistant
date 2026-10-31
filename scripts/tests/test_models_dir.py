"""Orden de resolución de la carpeta de modelos: --models-dir > env > .env.local > ./models."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import MODELS_DIR_KEY, ROOT, models_dir, read_env_local, write_env_local


@pytest.fixture
def env_local(tmp_path: Path) -> Path:
    p = tmp_path / ".env.local"
    write_env_local(MODELS_DIR_KEY, str(tmp_path / "from-file"), p)
    return p


def test_cli_wins_over_everything(
    tmp_path: Path, env_local: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MODELS_DIR_KEY, str(tmp_path / "from-env"))
    assert models_dir(str(tmp_path / "from-cli"), env_local) == (
        (tmp_path / "from-cli").resolve(),
        "--models-dir",
    )


def test_env_wins_over_file(
    tmp_path: Path, env_local: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(MODELS_DIR_KEY, str(tmp_path / "from-env"))
    assert models_dir(None, env_local)[1] == MODELS_DIR_KEY


def test_file_wins_over_default(
    tmp_path: Path, env_local: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(MODELS_DIR_KEY, raising=False)
    assert models_dir(None, env_local) == (
        (tmp_path / "from-file").resolve(),
        ".env.local",
    )


def test_default_is_repo_models(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MODELS_DIR_KEY, raising=False)
    assert models_dir(None, tmp_path / "missing.env")[0] == ROOT / "models"


def test_write_env_local_preserves_other_keys(tmp_path: Path) -> None:
    p = tmp_path / ".env.local"
    p.write_text("# comentario\nOTRA=1\n", encoding="utf-8")
    write_env_local(MODELS_DIR_KEY, "/x", p)
    assert read_env_local(p) == {"OTRA": "1", MODELS_DIR_KEY: "/x"}
