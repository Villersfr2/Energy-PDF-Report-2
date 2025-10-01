"""Tests rapides pour la fonction normalize_to_kwh."""

from __future__ import annotations

import ast
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "energy_pdf_report"
    / "__init__.py"
)


def _load_normalize_to_kwh() -> Callable[[float, str | None], float]:
    """Extraire la fonction normalize_to_kwh sans initialiser Home Assistant."""

    module_ast = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    function_node: ast.FunctionDef | None = None

    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name == "normalize_to_kwh":
            function_node = node
            break

    if function_node is None:
        raise AssertionError("normalize_to_kwh introuvable dans le module")

    compiled = compile(
        ast.Module(body=[function_node], type_ignores=[]),
        str(MODULE_PATH),
        "exec",
    )
    namespace: dict[str, object] = {"_LOGGER": logging.getLogger("test.normalize")}
    exec(compiled, namespace)
    return namespace["normalize_to_kwh"]  # type: ignore[index]


normalize_to_kwh = _load_normalize_to_kwh()


def test_wh_to_kwh_conversion():
    """64 000 Wh doivent devenir 64 kWh."""

    assert normalize_to_kwh(64_000, "Wh") == pytest.approx(64)


def test_mwh_to_kwh_conversion():
    """2 MWh doivent devenir 2000 kWh."""

    assert normalize_to_kwh(2, "MWh") == pytest.approx(2_000)


def test_kwh_remains_unchanged():
    """5 kWh restent 5 kWh."""

    assert normalize_to_kwh(5, "kWh") == pytest.approx(5)
