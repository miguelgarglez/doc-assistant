from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

PACKAGE = "doc_assistant"
ROOT_ENTRIES = {
    "__init__.py",
    "bootstrap.py",
    "config.py",
    "export_openapi.py",
    "feedback_export.py",
    "feedback_review.py",
    "history_clear.py",
}
FORBIDDEN = {
    "domain": {"api", "application", "infra", "bootstrap", "config"},
    "application": {"api", "infra", "bootstrap", "config"},
    "infra": {"api", "bootstrap", "config"},
    "api": {"infra", "bootstrap", "config"},
}
IO_MODULES = {"fastapi", "sqlite3", "httpx", "requests", "urllib", "socket", "pypdfium2"}


def architecture_errors(root: Path) -> list[str]:
    files = {}
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        files[".".join([PACKAGE, *parts])] = path
    graph: dict[str, set[str]] = {module: set() for module in files}
    errors = []
    for path in root.iterdir():
        if path.is_file() and path.suffix == ".py" and path.name not in ROOT_ENTRIES:
            errors.append(f"unexpected root entry: {path.name}")
        if path.is_dir() and path.name not in {
            "api",
            "application",
            "domain",
            "infra",
            "__pycache__",
        }:
            errors.append(f"unexpected root package: {path.name}")

    for module, path in files.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package = module if path.name == "__init__.py" else module.rpartition(".")[0]
        imports: set[str] = set()
        dynamic_names = {"__import__"}
        importlib_names = set()
        builtins_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
                    if alias.name == "importlib":
                        importlib_names.add(alias.asname or "importlib")
                    if alias.name == "builtins":
                        builtins_names.add(alias.asname or "builtins")
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = importlib.util.resolve_name(
                        "." * node.level + (node.module or ""), package
                    )
                else:
                    base = node.module or ""
                imports.add(base)
                for alias in node.names:
                    if alias.name == "*" and (base == PACKAGE or base.startswith(PACKAGE + ".")):
                        errors.append(f"{module}: wildcard internal import {base}")
                    if (base, alias.name) in {
                        ("importlib", "import_module"),
                        ("builtins", "__import__"),
                    }:
                        dynamic_names.add(alias.asname or alias.name)
                    candidate = f"{base}.{alias.name}"
                    if candidate in files:
                        imports.add(candidate)
        layer = module.split(".")[1] if module.count(".") else ""
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            dynamic = isinstance(fn, ast.Name) and fn.id in dynamic_names
            dynamic |= (
                isinstance(fn, ast.Attribute)
                and fn.attr == "import_module"
                and isinstance(fn.value, ast.Name)
                and fn.value.id in importlib_names
            )
            dynamic |= (
                isinstance(fn, ast.Attribute)
                and fn.attr == "__import__"
                and isinstance(fn.value, ast.Name)
                and fn.value.id in builtins_names
            )
            if dynamic:
                target = node.args[0] if node.args else None
                if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
                    errors.append(f"{module}: dynamic import with unknown target")
                elif target.value == PACKAGE or target.value.startswith((PACKAGE + ".", ".")):
                    errors.append(f"{module}: dynamic internal import {target.value}")
                elif (
                    layer in {"domain", "application"} and target.value.split(".")[0] in IO_MODULES
                ):
                    errors.append(f"{module}: forbidden dynamic import {target.value}")
        for target in imports:
            if layer in {"domain", "application"} and target.split(".")[0] in IO_MODULES:
                errors.append(f"{module}: forbidden external import {target}")
            if target == PACKAGE or target.startswith(PACKAGE + "."):
                components = target.split(".")
                for length in range(1, len(components) + 1):
                    dependency = ".".join(components[:length])
                    if dependency in files and dependency != module:
                        graph[module].add(dependency)

    for module, dependencies in graph.items():
        layer = module.split(".")[1] if module.count(".") else ""
        reachable: set[str] = set()
        pending = list(dependencies)
        while pending:
            dependency = pending.pop()
            if dependency in reachable:
                continue
            reachable.add(dependency)
            pending.extend(graph[dependency] - reachable)
        if module in reachable:
            errors.append(f"cycle involving {module}")
        for dependency in reachable:
            dep_layer = dependency.split(".")[1] if dependency.count(".") else ""
            if dep_layer in FORBIDDEN.get(layer, set()):
                errors.append(f"{module}: forbidden dependency {dependency}")
    return sorted(set(errors))


def test_package_architecture() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / PACKAGE
    assert architecture_errors(root) == []


def test_import_rules_cover_relative_transitive_cycles_and_dynamic_imports(tmp_path: Path) -> None:
    def write(name: str, text: str) -> None:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    write("__init__.py", "")
    write("domain/__init__.py", "")
    write("domain/value.py", "from . import helper\n")
    write("domain/helper.py", "from typing import Any\n")
    write("application/__init__.py", "")
    write("application/use.py", "from doc_assistant.domain import value\n")
    write("infra/__init__.py", "")
    write("infra/store.py", "from doc_assistant.application import use\n")
    write("api/__init__.py", "")
    write("api/routes.py", "from doc_assistant.application import use\n")
    assert architecture_errors(tmp_path) == []

    write(
        "domain/helper.py",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from doc_assistant.infra import store\n",
    )
    errors = architecture_errors(tmp_path)
    assert any("forbidden dependency" in error and "infra" in error for error in errors)
    assert any("cycle involving" in error for error in errors)

    write(
        "domain/helper.py",
        "from importlib import import_module as load\nload('doc_assistant.infra.store')\n",
    )
    assert any("dynamic internal import" in error for error in architecture_errors(tmp_path))
    write("domain/helper.py", "import sqlite3\n")
    assert any(
        "forbidden external import sqlite3" in error for error in architecture_errors(tmp_path)
    )

    write("domain/helper.py", "import builtins as b\nb.__import__('sqlite3')\n")
    assert any(
        "forbidden dynamic import sqlite3" in error for error in architecture_errors(tmp_path)
    )
    write("unexpected.py", "")
    assert any("unexpected root entry" in error for error in architecture_errors(tmp_path))
    write("domain/helper.py", "from doc_assistant.infra import *\n")
    assert any("wildcard internal import" in error for error in architecture_errors(tmp_path))
