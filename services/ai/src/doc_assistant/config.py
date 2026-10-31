"""Validated configuration loaded at the application boundary."""

import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

LLAMA_OCR_PORT_ENV = "DOC_ASSISTANT_OCR_PORT"
OLLAMA_URL = "http://127.0.0.1:11434"
_ENV_REF = re.compile(r"\$\{([A-Z][A-Z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: Any) -> Any:
    """Replaces ${NAME} and ${NAME:-default} in every string of the loaded YAML.
    A name without a value and without a default is an error, not an empty string."""
    if isinstance(value, str):

        def sub(m: re.Match[str]) -> str:
            found = os.environ.get(m.group(1))
            if found:
                return found
            if m.group(2) is None:
                raise ValueError(f"config usa ${{{m.group(1)}}} y la variable no está definida")
            return m.group(2)

        return _ENV_REF.sub(sub, value)
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value


def _checked_port(base_url: str) -> str:
    try:
        urlparse(base_url).port  # noqa: B018 - raises ValueError on a non numeric or out of range port
    except ValueError as e:
        raise ValueError(f"puerto no válido en {base_url!r}: revisa las variables *_PORT") from e
    return base_url


class EndpointConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(pattern=r"^https?://")
    endpoint: str = Field(pattern=r"^/")
    model: str = Field(min_length=1)
    timeout_s: float = Field(default=90, gt=0)
    dim: int | None = Field(default=None, gt=0)

    @field_validator("base_url")
    @classmethod
    def _check_port(cls, value: str) -> str:
        return _checked_port(value)

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

    @field_validator("base_url")
    @classmethod
    def _check_port(cls, value: str) -> str:
        return _checked_port(value)

    def ollama_url(self) -> str:
        """Ollama runtime: base_url is the llama endpoint unless the config points elsewhere."""
        llama_port = os.environ.get(LLAMA_OCR_PORT_ENV) or "8084"
        if self.base_url.rstrip("/") == f"http://127.0.0.1:{llama_port}":
            return OLLAMA_URL
        return self.base_url


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
    raw = expand_env(yaml.safe_load(path.read_text(encoding="utf-8")))
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
