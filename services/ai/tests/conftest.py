"""Fixtures compartidas: PDF sintético, factura, config temporal, fakes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from doc_assistant.model_fakes import FakeEmbedder, FakeReranker


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """PDF con título, secciones numeradas y pie de empresa."""
    path = tmp_path / "manual.pdf"
    c = Canvas(str(path), pagesize=A4)
    y = 800
    lines = [
        "Manual del Robot ACME-100",
        "1. Seguridad",
        "El robot debe operar a 24 V en todo momento.",
        "2. Instalacion",
        "Fijar la base con tornillos M6 antes de energizar.",
        "2.1. Cableado",
        "Usar cable de 2.5 mm2 para la alimentacion principal.",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 18
    c.drawString(50, 40, "ACME Robotics · Manual · 1")
    c.showPage()
    c.save()
    return path


@pytest.fixture
def invoice_json(tmp_path: Path) -> Path:
    path = tmp_path / "invoice.json"
    data = {
        "numero": "FAC-2024-001",
        "fecha": "2024-03-15",
        "cliente": "Acme Robotics SL",
        "total": "1200.00 EUR",
        "lineas": [
            {"descripcion": "Motor brushless", "cantidad": 2, "precio": "400.00 EUR"},
            {"descripcion": "Controlador", "cantidad": 1, "precio": "400.00 EUR"},
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    cfg = {
        "db": str(tmp_path / "test.db"),
        "docs": str(tmp_path / "docs"),
        "data_dir": str(tmp_path / "data"),
        "llm": {
            "base_url": "http://127.0.0.1:8081",
            "endpoint": "/v1/chat/completions",
            "model": "llm-local",
            "timeout_s": 90,
        },
        "embeddings": {
            "base_url": "http://127.0.0.1:8082",
            "endpoint": "/v1/embeddings",
            "model": "emb-local",
            "timeout_s": 90,
            "dim": 8,
        },
        "reranker": {
            "base_url": "http://127.0.0.1:8083",
            "endpoint": "/v1/rerank",
            "model": "rerank-local",
            "timeout_s": 90,
        },
        "top_k": 5,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(cfg), encoding="utf-8")
    return path


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder(dim=8)


@pytest.fixture
def fake_reranker() -> FakeReranker:
    return FakeReranker()
