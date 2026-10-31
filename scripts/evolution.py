"""Galería de evolución: capturas de cada tag v* extraídas de git, sin inventar nada.

Uso: `mise run evolution`. Reescribe evidence/evolution/ entera a partir de los tags
anotados (fecha = commit etiquetado; texto = mensaje del tag; capturas = git show).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evidence" / "evolution"
SHOTS = "evidence/screenshots"
TRASH = ROOT / "_trash" / "evolution"


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
    return [tuple(line.split("|")) for line in out.splitlines() if line]  # type: ignore[misc]


def main() -> int:
    if OUT.exists():  # regla del repo: no se borra, se aparta
        TRASH.mkdir(parents=True, exist_ok=True)
        dest = TRASH / f"evolution-{len(list(TRASH.iterdir()))}"
        shutil.move(str(OUT), dest)
    OUT.mkdir(parents=True)
    lines = [
        "# Evolución por versión",
        "",
        "Generado por `mise run evolution` (scripts/evolution.py) desde los tags anotados de git.",
        "Las capturas son las que estaban versionadas en ese tag (`git show <tag>:evidence/screenshots/…`);",
        "el texto es el mensaje del tag.",
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
    for tag, sha, date in found:
        msg = git("tag", "-l", "--format=%(contents)", tag).strip().splitlines()
        title, body = msg[0], "\n".join(msg[1:]).strip()
        lines += [f"## {tag} · {date} · commit `{sha}`", "", f"**{title}**", "", body, ""]
        names = [
            n
            for n in git("ls-tree", "-r", "--name-only", tag, "--", SHOTS).splitlines()
            if n.endswith(".png")
        ]
        if not names:
            lines += ["_Sin capturas en esta versión._", ""]
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
