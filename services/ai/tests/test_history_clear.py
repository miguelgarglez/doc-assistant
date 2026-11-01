import pytest

from doc_assistant.history_clear import clear


def test_clear_only_calls_local_proxy_with_origin(monkeypatch):
    calls = []

    class Response:
        status = 200

        def read(self):
            return b'{"deleted": 4}'

    class Connection:
        def __init__(self, host, port, timeout):
            calls.append((host, port, timeout))

        def request(self, method, path, headers):
            calls.append((method, path, headers))

        def getresponse(self):
            return Response()

        def close(self):
            calls.append("closed")

    monkeypatch.setattr("doc_assistant.history_clear.http.client.HTTPConnection", Connection)
    assert clear("http://localhost:3300") == 4
    assert calls == [
        ("127.0.0.1", 3300, 10),
        ("DELETE", "/api/history/conversations", {"Origin": "http://localhost:3300"}),
        "closed",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:3300",
        "https://127.0.0.1:3300",
        "http://127.0.0.1",
        "http://127.0.0.1:3300/path",
        "http://user@127.0.0.1:3300",
    ],
)
def test_clear_refuses_nonlocal_or_ambiguous_destinations(url):
    with pytest.raises(ValueError):
        clear(url)
