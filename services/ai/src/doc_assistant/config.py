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


class OcrConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # "llama": GLM-OCR GGUF en llama-server (por defecto, va en el ZIP); "ollama": fallback
    runtime: Literal["llama", "ollama"] = "llama"
    base_url: str = Field(default="http://127.0.0.1:8084", pattern=r"^https?://")
    model: str = Field(default="glm-ocr", min_length=1)
    timeout_s: float = Field(default=300, gt=0)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    db: Path
    docs: Path
    data_dir: Path
    llm: EndpointConfig
    embeddings: EndpointConfig
    reranker: EndpointConfig
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    upload_pdf_max_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    upload_image_max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    upload_pdf_max_pages: int = Field(default=200, gt=0)
    top_k: int = Field(default=5, gt=0)
    answer_mode: Literal["decide_first", "evidence_first"] = "decide_first"
    # How inline citations are placed: "model" asks the LLM for segments and validates them,
    # "rules" assigns them from lexical overlap, "off" leaves citations after the answer.
    inline_citations: Literal["model", "rules", "off"] = "rules"
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
    cfg.data_dir = (path.parent / cfg.data_dir).resolve()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    if not cfg.data_dir.is_dir():
        raise ValueError("data_dir must be a directory")
    if cfg.embeddings.dim is None:
        raise ValueError("embeddings.dim is required")
    return cfg
