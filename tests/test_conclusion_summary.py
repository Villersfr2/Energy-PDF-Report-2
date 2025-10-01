"""Tests for the conclusion summary helpers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from homeassistant.const import ENERGY_KILO_WATT_HOUR

sys.path.append(str(Path(__file__).resolve().parents[1]))

from custom_components.energy_pdf_report import (  # noqa: E402  # pylint: disable=wrong-import-position
    _prepare_conclusion_summary,
    MetricDefinition,
)


def _metadata(unit: str):
    return (0, {"unit_of_measurement": unit})


def test_prepare_conclusion_summary_converts_mixed_energy_units():
    metrics = [
        MetricDefinition("Production solaire", "solar"),
        MetricDefinition("Import réseau", "grid_in_wh"),
        MetricDefinition("Export réseau", "grid_out_wh"),
        MetricDefinition("Consommation appareils", "device"),
        MetricDefinition("Charge batterie", "charge_wh"),
        MetricDefinition("Décharge batterie", "discharge"),
    ]

    totals = {
        "solar": 5.0,  # already in kWh
        "grid_in_wh": 2000.0,  # Wh
        "grid_out_wh": 500.0,  # Wh
        "device": 4.0,  # kWh
        "charge_wh": 1000.0,  # Wh
        "discharge": 0.5,  # kWh
    }

    metadata = {
        "solar": _metadata(ENERGY_KILO_WATT_HOUR),
        "grid_in_wh": _metadata("Wh"),
        "grid_out_wh": _metadata("Wh"),
        "device": _metadata(ENERGY_KILO_WATT_HOUR),
        "charge_wh": _metadata("Wh"),
        "discharge": _metadata(ENERGY_KILO_WATT_HOUR),
    }

    summary = _prepare_conclusion_summary(metrics, totals, metadata)

    assert summary is not None
    assert summary.energy_unit == ENERGY_KILO_WATT_HOUR
    assert summary.production == pytest.approx(5.0)
    assert summary.imported == pytest.approx(2.0)
    assert summary.exported == pytest.approx(0.5)
    assert summary.consumption == pytest.approx(4.0)
    assert summary.charge == pytest.approx(1.0)
    assert summary.discharge == pytest.approx(0.5)
    assert summary.direct == pytest.approx(3.5)
    assert summary.indirect == pytest.approx(0.5)
    assert summary.total_estimated_consumption == pytest.approx(6.0)
    assert summary.untracked_consumption == pytest.approx(2.0)
    assert summary.formatted["imported"].endswith(f" {ENERGY_KILO_WATT_HOUR}")
    assert summary.formatted["untracked_consumption"].startswith("2.000")
