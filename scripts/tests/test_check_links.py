from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_links import BrokenLink, broken_links


def test_local_links_resolve_from_each_document(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    readme = docs / "README.md"
    target = docs / "guide with spaces.md"
    target.write_text("# Guía\n", encoding="utf-8")
    readme.write_text(
        "[guía](guide%20with%20spaces.md#guía)\n"
        "[sección](#local)\n"
        "[web](https://example.com/missing)\n",
        encoding="utf-8",
    )

    assert broken_links(tmp_path, [readme, target]) == []


def test_missing_local_link_reports_source_line_and_target(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Inicio\n\n[roto](docs/missing.md)\n", encoding="utf-8")

    assert broken_links(tmp_path, [readme]) == [BrokenLink(Path("README.md"), 3, "docs/missing.md")]
