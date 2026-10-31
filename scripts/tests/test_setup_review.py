import hashlib
import io
import sys
import urllib.error
import urllib.request
import zipfile
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import setup


def test_download_complete_and_416(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"correct"
    digest = hashlib.sha256(content).hexdigest()
    dest = tmp_path / "asset"
    part = tmp_path / "asset.part"
    part.write_bytes(content)
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: pytest.fail("network requested"))
    setup.download("https://example.test", dest, digest, len(content))
    assert dest.read_bytes() == content
    part.write_bytes(b"bad")
    calls = []

    class Response(io.BytesIO):
        status = 200

    def request(req: urllib.request.Request, **kwargs: Any) -> Response:
        calls.append(req)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 416, "range", Message(), None)
        return Response(content)

    monkeypatch.setattr(urllib.request, "urlopen", request)
    setup.download("https://example.test", dest, digest)
    assert dest.read_bytes() == content
    assert (tmp_path / "asset.part.bad").read_bytes() == b"bad"


def test_install_llama_publishes_version_and_skips_matching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vendor = tmp_path / "vendor" / "llama"
    archive_dir = tmp_path / "archives"
    archive_dir.mkdir()
    archive = archive_dir / "llama.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("llama-server", "binary")
    monkeypatch.setattr(setup, "VENDOR", vendor)
    monkeypatch.setattr(setup, "ARCHIVES", archive_dir)
    monkeypatch.setattr(setup, "IS_WIN", False)
    monkeypatch.setattr(setup, "llama_exe", lambda: vendor / "llama-server")
    monkeypatch.setattr(setup, "llama_platform", lambda: ("test", "zip"))
    monkeypatch.setattr(
        setup,
        "ASSETS",
        {
            "llama_cpp": {
                "tag": "v1",
                "url": "https://x/llama.zip",
                "sha256": {"test": setup.sha256(archive)},
            }
        },
    )
    setup.install_llama()
    assert (vendor / "VERSION").read_text().strip() == "v1"
    archive.rename(archive_dir / "unused")
    setup.install_llama()
