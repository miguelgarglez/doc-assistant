from decimal import Decimal

from doubles import FakeLLM, FakeOCR

from doc_assistant.application.invoices.extract import extract_invoice, parse_es_decimal


def test_model_overload_and_timeout_are_preserved_at_transport_boundary(monkeypatch):
    import pytest
    import requests

    from doc_assistant.application.ports.models import AdapterBusy, AdapterTimeout
    from doc_assistant.infra.models.http import _request_json

    for status in (429, 503):
        response = requests.Response()
        response.status_code = status
        monkeypatch.setattr("requests.request", lambda *a, result=response, **k: result)
        with pytest.raises(AdapterBusy) as caught:
            _request_json("POST", "http://model", timeout=1)
        assert caught.value.code == "model_busy"
        assert "http://" not in caught.value.public_message

    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr("requests.request", timeout)
    with pytest.raises(AdapterTimeout) as caught:
        _request_json("POST", "http://model", timeout=1)
    assert caught.value.code == "model_timeout"


def test_decimal_requires_complete_valid_value():
    assert parse_es_decimal("1.234,56") == Decimal("1234.56")
    assert parse_es_decimal("abc123") is None
    assert parse_es_decimal("1.2.3") is None


def test_unsubstantiated_text_is_null_and_flagged():
    result = extract_invoice(
        b"image",
        ocr=FakeOCR("Factura F-1"),
        llm=FakeLLM({"invoice_number": "F-1", "seller_name": "Inventado"}),
    )
    assert result["record"]["emisor"] is None
    assert result["flags"]["emisor"] == "sin_evidencia"


def test_adapters_reject_invalid_indices_and_dimensions(monkeypatch):
    import pytest

    from doc_assistant.application.ports.models import AdapterError
    from doc_assistant.infra.models.http import HttpEmbedder, HttpReranker

    monkeypatch.setattr(
        "doc_assistant.infra.models.http._request_json",
        lambda *a, **k: {"data": [{"index": 0, "embedding": [1.0]}]},
    )
    with pytest.raises(AdapterError):
        HttpEmbedder("url", "model", 1, 2).embed(["a"])
    monkeypatch.setattr(
        "doc_assistant.infra.models.http._request_json",
        lambda *a, **k: {"results": [{"index": 2, "relevance_score": 1}]},
    )
    with pytest.raises(AdapterError):
        HttpReranker("url", "model", 1).rerank("q", ["a"])


def test_adapter_cardinality_and_duplicate_indices(monkeypatch):
    import pytest

    from doc_assistant.application.ports.models import AdapterError
    from doc_assistant.infra.models.http import HttpEmbedder, HttpReranker

    for rows in ([{"index": 0, "embedding": [1]}], [{"index": 0, "embedding": [1]}] * 2):
        monkeypatch.setattr(
            "doc_assistant.infra.models.http._request_json",
            lambda *a, rows=rows, **k: {"data": rows},
        )
        with pytest.raises(AdapterError):
            HttpEmbedder("url", "m", 1, 1).embed(["a", "b"])
    for rows in ([{"index": 0, "relevance_score": 1}], [{"index": 0, "relevance_score": 1}] * 2):
        monkeypatch.setattr(
            "doc_assistant.infra.models.http._request_json",
            lambda *a, rows=rows, **k: {"results": rows},
        )
        with pytest.raises(AdapterError):
            HttpReranker("url", "m", 1).rerank("q", ["a", "b"])
