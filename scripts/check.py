"""CI local: lint, tipos, tests, enlaces y drift del contrato OpenAPI -> cliente TS.

Uso: python scripts/check.py [--only TAREA]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from _common import ROOT

AI = ROOT / "services" / "ai"
CONTRACT = ["services/ai/openapi.json", "apps/web/src/lib/api/schema.d.ts"]
TESTS = {
    "test": ["tests/unit", "tests/integration"],
    "test-unit": ["tests/unit"],
    "test-integration": ["tests/integration"],
    "test-live": ["tests/live"],
    "test-architecture": ["tests/unit/test_architecture.py"],
}


def tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"[check] no encuentro '{name}' en el PATH")
    return path


def step(label: str, cmd: list[str], cwd: Path) -> None:
    print(
        f"[check] {label}: {' '.join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd))}",
        flush=True,
    )
    if subprocess.run(cmd, cwd=cwd, check=False).returncode != 0:
        raise SystemExit(f"[check] FALLO en {label}")


def gen_client() -> None:
    step("export openapi", [sys.executable, "-m", "doc_assistant.export_openapi"], AI)
    step("gen cliente TS", [tool("pnpm"), "--filter", "web", "gen:api"], ROOT)


def service_tests(scope: str = "test") -> None:
    step(scope, [sys.executable, "-m", "pytest", "-q", *TESTS[scope]], AI)


def python_checks() -> None:
    py = [sys.executable, "-m"]
    step("ruff", [*py, "ruff", "check", ".", "../../scripts"], AI)
    step("ruff format", [*py, "ruff", "format", "--check", ".", "../../scripts"], AI)
    step("mypy", [*py, "mypy", "src"], AI)
    step("mypy scripts", [*py, "mypy", "--strict", "."], ROOT / "scripts")
    service_tests()
    step("pytest scripts", [*py, "pytest", "-q", "tests"], ROOT / "scripts")
    step(
        "enlaces Markdown",
        [sys.executable, str(ROOT / "scripts" / "check_links.py")],
        ROOT,
    )


def web_checks() -> None:
    pnpm = tool("pnpm")
    step("eslint", [pnpm, "--filter", "web", "lint"], ROOT)
    step("typecheck", [pnpm, "--filter", "web", "typecheck"], ROOT)


def build() -> None:
    step("next build", [tool("pnpm"), "--filter", "web", "build"], ROOT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=[*TESTS, "build", "gen-client"])
    a = ap.parse_args()
    if a.only in TESTS:
        service_tests(a.only)
    elif a.only == "build":
        build()
    elif a.only == "gen-client":
        gen_client()
    else:
        python_checks()
        gen_client()
        step(
            "sin drift del contrato",
            [tool("git"), "diff", "--exit-code", "--", *CONTRACT],
            ROOT,
        )
        web_checks()
        build()
        print("[check] OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
