"""Galería de evolución: capturas de cada tag v* extraídas de git, sin inventar nada.

Uso: `mise run evolution`. Reescribe evidence/evolution/ entera a partir de los tags
anotados (fecha = commit etiquetado; texto = mensaje del tag; capturas = git show).
Desde v0.13.0 cada versión enseña solo las capturas que cambian respecto a la anterior;
las galerías anteriores se conservan completas. Los tags con sufijo (`-pre-merge`) no
tienen galería.
Una nota que no cabe en el mensaje del tag va en docs/evolution-notes/<tag>.md.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "evolution"
SHOTS = "evidence/screenshots"
NOTES = ROOT / "docs" / "evolution-notes"
TRASH = ROOT / "_trash" / "evolution"
DEDUPE_FROM = (0, 13, 0)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def tags() -> list[tuple[str, str, str]]:
    """(tag, sha corto, fecha ISO del commit) en orden cronológico."""
    out = git(
        "for-each-ref",
        "--sort=*committerdate",
        "--format=%(refname:short)|%(*objectname:short)|%(*committerdate:format:%Y-%m-%d %H:%M %z)",
        "refs/tags/v*",
    )
    rows = [tuple(line.split("|")) for line in out.splitlines() if line]
    return [row for row in rows if "-" not in row[0]]  # type: ignore[misc]


def version_of(tag: str) -> tuple[int, ...]:
    return tuple(int(part) for part in tag.removeprefix("v").split("."))


def shots_at(tag: str) -> dict[str, str]:
    """Nombre de cada captura PNG del tag y el hash de su contenido."""
    out: dict[str, str] = {}
    for line in git("ls-tree", "-r", tag, "--", SHOTS).splitlines():
        meta, name = line.split("\t", 1)
        if name.endswith(".png"):
            out[name] = meta.split()[2]
    return out


def main() -> int:
    if OUT.exists():  # regla del repo: no se borra, se aparta
        TRASH.mkdir(parents=True, exist_ok=True)
        dest = TRASH / f"evolution-{len(list(TRASH.iterdir()))}"
        shutil.move(str(OUT), dest)
    OUT.mkdir(parents=True)
    lines = [
        "# Evolución por versión",
        "",
        "Galerías históricas generadas por `mise run evolution` (scripts/evolution.py) desde los tags anotados de git.",
        "Las capturas son las versionadas en cada tag (`git show <tag>:evidence/screenshots/…`);",
        "desde v0.13.0 solo se enseñan las que cambian respecto a la versión anterior.",
        "El texto es el mensaje del tag y, si existe, su nota en `docs/evolution-notes/`.",
        "",
        "Nota de honestidad: al publicar se reescribió el historial (nombre público y fixtures neutros).",
        "Las capturas versionadas de cada commit se regeneraron entonces ejecutando el e2e del código",
        "de ese mismo commit, porque las originales mostraban la marca y fixtures anteriores.",
        "",
    ]
    found = tags()
    if not found:
        print("[evolution] no hay tags v*", file=sys.stderr)
        return 1
    previous: dict[str, str] = {}
    for tag, sha, date in found:
        msg = git("tag", "-l", "--format=%(contents)", tag).strip().splitlines()
        title, body = msg[0], "\n".join(msg[1:]).strip()
        lines += [f"## {tag} · {date} · commit `{sha}`", "", f"**{title}**", "", body, ""]
        note = NOTES / f"{tag}.md"
        if note.exists():
            lines += [note.read_text(encoding="utf-8").strip(), ""]
        current = shots_at(tag)
        dedupe = version_of(tag) >= DEDUPE_FROM
        names = [n for n, blob in current.items() if not dedupe or previous.get(n) != blob]
        if current:
            previous = current
        if not names:
            lines += [
                "_Sin capturas nuevas en esta versión._"
                if current
                else "_Sin capturas en esta versión._",
                "",
            ]
            continue
        (OUT / tag).mkdir()
        for name in names:
            blob = subprocess.run(
                ["git", "show", f"{tag}:{name}"], cwd=ROOT, check=True, capture_output=True
            ).stdout
            (OUT / tag / Path(name).name).write_bytes(blob)
            lines.append(f"![{tag} {Path(name).stem}]({tag}/{Path(name).name})")
        lines.append("")
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[evolution] {len(found)} tags → {OUT.relative_to(ROOT)}/README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
