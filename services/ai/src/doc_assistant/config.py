"""Validated configuration loaded at the application boundary."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class EndpointConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(pattern=r"^https?://")
    endpoint: str = Field(pattern=r"^/")
    model: str = Field(min_length=1)
    timeout_s: float = Field(default=90, gt=0)
    dim: int | None = Field(default=None, gt=0)

    @property
    def url(self) -> str:
        return self.base_url.rstrip("/") + self.endpoint


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    db: Path
    docs: Path
    llm: EndpointConfig
    embeddings: EndpointConfig
    reranker: EndpointConfig
    top_k: int = Field(default=5, gt=0)
    answer_mode: Literal["decide_first", "evidence_first"] = "decide_first"
    path: Path = Path("config.yaml")


def load_config(path: str | Path) -> AppConfig:
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError("Configuration must be a mapping")
    raw["path"] = path
    cfg = AppConfig.model_validate(raw)
    # Relative paths are anchored to the configuration file, not the process cwd.
    cfg.db = (path.parent / cfg.db).resolve()
    cfg.docs = (path.parent / cfg.docs).resolve()
    if cfg.embeddings.dim is None:
        raise ValueError("embeddings.dim is required")
    return cfg
