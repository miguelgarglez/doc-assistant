"""Comprueba que los enlaces locales de Markdown apunten a rutas existentes."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from _common import ROOT

LINK = re.compile(r"!?\[[^\]]*]\((?P<target><[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)")
EXCLUDED_DIRS = frozenset({"node_modules", ".venv", ".next", "vendor", "models", "data"})


@dataclass(frozen=True)
class BrokenLink:
    source: Path
    line: int
    target: str


def tracked_markdown(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        return [root / name.decode() for name in result.stdout.split(b"\0") if name]
    return sorted(
        path
        for path in root.rglob("*.md")
        if not EXCLUDED_DIRS.intersection(path.relative_to(root).parts)
    )


def local_path(source: Path, target: str) -> Path | None:
    raw = target.removeprefix("<").removesuffix(">")
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = Path(unquote(parsed.path))
    if path.is_absolute():
        return None
    return (source.parent / path).resolve()


def broken_links(root: Path, files: list[Path] | None = None) -> list[BrokenLink]:
    issues: list[BrokenLink] = []
    for source in files if files is not None else tracked_markdown(root):
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            for match in LINK.finditer(line):
                target = match.group("target")
                path = local_path(source, target)
                if path is not None and not path.exists():
                    issues.append(BrokenLink(source.relative_to(root), line_number, target))
    return issues


def main() -> int:
    issues = broken_links(ROOT)
    for issue in issues:
        print(f"{issue.source}:{issue.line}: enlace local inexistente: {issue.target}")
    if issues:
        return 1
    print(f"[links] OK: {len(tracked_markdown(ROOT))} archivos Markdown")
    return 0


if __name__ == "__main__":
    sys.exit(main())
