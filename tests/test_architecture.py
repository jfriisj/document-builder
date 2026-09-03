import ast
from pathlib import Path
from unittest.mock import patch
import pytest

SRC_DIR = Path(__file__).parent.parent / "src"
CORE_DIR = SRC_DIR / "hashoej_document_builder" / "core"
ROOT_INIT = SRC_DIR / "hashoej_document_builder" / "__init__.py"

FORBIDDEN_CORE_TARGETS = {
    "fastapi",
    "starlette",
    "uvicorn",
    "httpx",
    "hashoej_document_builder.web",
}

FORBIDDEN_ROOT_TARGETS = {
    "fastapi",
    "starlette",
    "uvicorn",
    "httpx",
    "hashoej_document_builder.web",
}


def get_imported_targets_from_ast(
    tree: ast.AST, file_path: Path, src_dir: Path
) -> list[tuple[int, str]]:
    """Extract all resolved imported module targets (absolute or resolved relative) from an AST."""
    rel_file = file_path.resolve().relative_to(src_dir.resolve())
    pkg_parts = rel_file.parent.parts

    imported_targets: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_targets.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base_module = node.module or ""
            else:
                # Relative import: level 1 is current package, level 2 is parent, etc.
                if node.level > len(pkg_parts):
                    base_parts = ()
                else:
                    base_parts = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                if node.module:
                    target_parts = base_parts + tuple(node.module.split("."))
                else:
                    target_parts = base_parts
                base_module = ".".join(target_parts)

            if base_module:
                imported_targets.append((node.lineno, base_module))

            for alias in node.names:
                if base_module:
                    imported_targets.append((node.lineno, f"{base_module}.{alias.name}"))
                else:
                    imported_targets.append((node.lineno, alias.name))

    return imported_targets


def check_forbidden_imports(
    file_path: Path, src_dir: Path, forbidden_prefixes: set[str]
) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    targets = get_imported_targets_from_ast(tree, file_path, src_dir)
    violations: list[str] = []
    for lineno, target in targets:
        for forbidden in forbidden_prefixes:
            if target == forbidden or target.startswith(forbidden + "."):
                violations.append(
                    f"{file_path.name}:{lineno} imports '{target}' (forbidden: '{forbidden}')"
                )
    return violations


def test_core_does_not_import_web_or_fastapi() -> None:
    """Verify hashoej_document_builder.core remains completely independent of web layer and FastAPI."""
    assert CORE_DIR.exists() and CORE_DIR.is_dir()

    python_files = list(CORE_DIR.rglob("*.py"))
    assert len(python_files) > 0, "No python files found in core directory"

    all_violations: list[str] = []
    for file_path in python_files:
        violations = check_forbidden_imports(file_path, SRC_DIR, FORBIDDEN_CORE_TARGETS)
        all_violations.extend(violations)

    assert not all_violations, f"Architectural boundary violated in core: {all_violations}"


def test_root_init_does_not_import_web_or_runtime_dependencies() -> None:
    """Verify hashoej_document_builder.__init__.py is clean and free of web/runtime dependencies."""
    assert ROOT_INIT.exists()

    violations = check_forbidden_imports(ROOT_INIT, SRC_DIR, FORBIDDEN_ROOT_TARGETS)
    assert not violations, f"Root __init__.py contains forbidden imports: {violations}"


@pytest.mark.parametrize(
    "code_snippet,expected_match",
    [
        ("from ..web import app", "hashoej_document_builder.web"),
        ("from ..web.app import app", "hashoej_document_builder.web"),
        ("from .. import web", "hashoej_document_builder.web"),
        ("from hashoej_document_builder import web", "hashoej_document_builder.web"),
        ("import hashoej_document_builder.web", "hashoej_document_builder.web"),
        ("import hashoej_document_builder.web.app", "hashoej_document_builder.web"),
        ("import fastapi", "fastapi"),
        ("from fastapi import FastAPI", "fastapi"),
        ("import starlette", "starlette"),
        ("from starlette.requests import Request", "starlette"),
        ("import uvicorn", "uvicorn"),
        ("import httpx", "httpx"),
    ],
)
def test_boundary_checker_detects_forbidden_patterns(code_snippet: str, expected_match: str) -> None:
    """Ensure the AST analyzer correctly flags both absolute and relative forbidden imports."""
    dummy_core_file = CORE_DIR / "models.py"
    tree = ast.parse(code_snippet, filename="dummy.py")
    targets = get_imported_targets_from_ast(tree, dummy_core_file, SRC_DIR)

    matches = [
        target
        for _, target in targets
        if target == expected_match or target.startswith(expected_match + ".")
    ]
    assert matches, f"Failed to detect forbidden import in '{code_snippet}' for '{expected_match}'"


def test_boundary_checker_allows_valid_core_imports() -> None:
    """Ensure valid imports within core or standard library are not falsely flagged."""
    dummy_core_file = CORE_DIR / "models.py"
    valid_code = """
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .models import TemplatePackage
from hashoej_document_builder.core.models import GenerationSession
"""
    tree = ast.parse(valid_code, filename="valid.py")
    targets = get_imported_targets_from_ast(tree, dummy_core_file, SRC_DIR)

    violations = [
        target
        for _, target in targets
        for forbidden in FORBIDDEN_CORE_TARGETS
        if target == forbidden or target.startswith(forbidden + ".")
    ]
    assert not violations, f"Valid imports were incorrectly flagged: {violations}"


def test_web_cli_main() -> None:
    """Verify that web CLI entrypoint calls uvicorn.run."""
    from hashoej_document_builder.web.cli import main

    with patch("uvicorn.run") as mock_run:
        main()
        mock_run.assert_called_once_with(
            "hashoej_document_builder.web.app:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
        )


