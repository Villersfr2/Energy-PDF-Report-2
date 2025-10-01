"""Tests rapides pour la fonction normalize_to_kwh."""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "energy_pdf_report"
    / "__init__.py"
)


def _load_helpers() -> dict[str, object]:
    """Extraire les fonctions utiles du module principal sans Home Assistant."""

    module_ast = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    needed_assigns = {"_ORIGINAL_UNIT_KEY", "_UNIT_WARNING_LOGGED_KEY"}
    needed_functions = {"normalize_to_kwh", "_calculate_totals"}

    selected: list[ast.stmt] = [
        ast.ImportFrom(
            module="__future__",
            names=[ast.alias(name="annotations", asname=None)],
            level=0,
        )
    ]

    for node in module_ast.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in needed_assigns:
                    selected.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name in needed_functions:
            selected.append(node)

    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    compiled = compile(module, str(MODULE_PATH), "exec")
    namespace: dict[str, object] = {
        "_LOGGER": logging.getLogger("test.normalize"),
        "logging": logging,
    }
    exec(compiled, namespace)
    return namespace


HELPERS = _load_helpers()
normalize_to_kwh = HELPERS["normalize_to_kwh"]  # type: ignore[index]
calculate_totals = HELPERS["_calculate_totals"]  # type: ignore[index]
ORIGINAL_UNIT_KEY = HELPERS["_ORIGINAL_UNIT_KEY"]  # type: ignore[index]


class _MetricStub:
    """Représentation minimale d'une statistique pour les tests."""

    def __init__(self, statistic_id: str) -> None:
        self.statistic_id = statistic_id
        self.category = "Test"


def test_wh_to_kwh_conversion():
    """64 000 Wh doivent devenir 64 kWh."""

    assert normalize_to_kwh(64_000, "Wh") == pytest.approx(64)


def test_mwh_to_kwh_conversion():
    """2 MWh doivent devenir 2000 kWh."""

    assert normalize_to_kwh(2, "MWh") == pytest.approx(2_000)


def test_kwh_remains_unchanged():
    """5 kWh restent 5 kWh."""

    assert normalize_to_kwh(5, "kWh") == pytest.approx(5)


def test_milliwatt_hours_are_supported():
    """1 500 000 mWh deviennent 1,5 kWh."""

    assert normalize_to_kwh(1_500_000, "mWh") == pytest.approx(1.5)


def test_calculate_totals_converts_wh_rows():
    """Les totaux sont convertis en kWh lorsque l'unité d'origine est Wh."""

    metadata = {
        "sensor.test_energy": (
            0,
            {
                ORIGINAL_UNIT_KEY: "Wh",
                "unit_of_measurement": "kWh",
            },
        )
    }

    stats = {"sensor.test_energy": [{"change": 64_462.0}]}
    totals = calculate_totals([_MetricStub("sensor.test_energy")], stats, metadata)

    assert totals["sensor.test_energy"] == pytest.approx(64.462)
    assert metadata["sensor.test_energy"][1]["unit_of_measurement"] == "kWh"


def test_calculate_totals_handles_missing_original_unit():
    """La conversion fonctionne même sans méta donnée interne dédiée."""

    metadata = {
        "sensor.test_energy": (
            0,
            {
                "unit_of_measurement": "Wh",
            },
        )
    }

    stats = {"sensor.test_energy": [{"change": 64_462.0}]}
    totals = calculate_totals([_MetricStub("sensor.test_energy")], stats, metadata)

    assert totals["sensor.test_energy"] == pytest.approx(64.462)
    assert metadata["sensor.test_energy"][1]["unit_of_measurement"] == "kWh"
