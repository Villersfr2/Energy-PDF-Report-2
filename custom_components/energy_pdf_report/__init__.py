"""Intégration personnalisée pour générer un rapport énergie en PDF."""

from __future__ import annotations

import calendar

import inspect
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from decimal import Decimal

from pathlib import Path
from typing import Any, Iterable, Mapping, TYPE_CHECKING
from homeassistant.core import async_get_hass
import voluptuous as vol

from homeassistant.components import persistent_notification, recorder
from homeassistant.components.recorder import statistics as recorder_statistics
from homeassistant.components.recorder.models.statistics import StatisticMetaData
from homeassistant.components.recorder.statistics import StatisticsRow
from homeassistant.const import CONF_FILENAME, UnitOfEnergy
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from homeassistant.components.energy.data import async_get_manager

from .const import (

    CONF_CO2,
    CONF_CO2_ELECTRICITY,
    CONF_CO2_GAS,
    CONF_CO2_SAVINGS,
    CONF_CO2_WATER,

    CONF_DASHBOARD,
    CONF_DEFAULT_REPORT_TYPE,
    CONF_END_DATE,
    CONF_FILENAME_PATTERN,
    CONF_OUTPUT_DIR,
    CONF_PERIOD,
    CONF_PRICE,
    CONF_PRICE_ELECTRICITY_EXPORT,
    CONF_PRICE_ELECTRICITY_IMPORT,
    CONF_PRICE_GAS,
    CONF_PRICE_WATER,
    CONF_START_DATE,
    CONF_LANGUAGE,
    CONF_OPENAI_API_KEY,
    DEFAULT_CO2,
    DEFAULT_CO2_ELECTRICITY_SENSOR,
    DEFAULT_CO2_GAS_SENSOR,
    DEFAULT_CO2_WATER_SENSOR,
    DEFAULT_CO2_SAVINGS_SENSOR,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LANGUAGE,
    DEFAULT_PERIOD,
    DEFAULT_PRICE,
    DEFAULT_PRICE_ELECTRICITY_EXPORT_SENSOR,
    DEFAULT_PRICE_ELECTRICITY_IMPORT_SENSOR,
    DEFAULT_PRICE_GAS_SENSOR,
    DEFAULT_PRICE_WATER_SENSOR,
    DEFAULT_REPORT_TYPE,
    DOMAIN,
    SUPPORTED_LANGUAGES,
    SERVICE_GENERATE_REPORT,
    VALID_PERIODS,
)
from .ai_helper import FALLBACK_MESSAGE, generate_advice
from .pdf import EnergyPDFBuilder, TableConfig, _decorate_category

from .translations import ReportTranslations, get_report_translations


if TYPE_CHECKING:
    from homeassistant.components.energy.data import EnergyPreferences

_LOGGER = logging.getLogger(__name__)

_RECORDER_METADATA_REQUIRES_HASS: bool | None = None


SERVICE_GENERATE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_START_DATE): cv.date,
        vol.Optional(CONF_END_DATE): cv.date,
        vol.Optional(CONF_PERIOD): vol.In(VALID_PERIODS),
        vol.Optional(CONF_FILENAME): cv.string,

        vol.Optional(CONF_OUTPUT_DIR): cv.string,

        vol.Optional(CONF_LANGUAGE): vol.In(SUPPORTED_LANGUAGES),

        vol.Optional(CONF_DASHBOARD): cv.string,
        vol.Optional(CONF_CO2): cv.boolean,
        vol.Optional(CONF_PRICE): cv.boolean,
    }
)


DATA_SERVICES_REGISTERED = "_services_registered"

@dataclass(slots=True)
class MetricDefinition:
    """Représentation d'une statistique à inclure dans le rapport."""

    category: str
    statistic_id: str



@dataclass(frozen=True, slots=True)
class CO2SensorDefinition:
    """Décrit un capteur CO₂ suivi dans le rapport."""

    entity_id: str
    translation_key: str
    is_saving: bool



@dataclass(frozen=True, slots=True)
class PriceSensorDefinition:
    """Décrit un capteur de coûts/compensations suivi dans le rapport."""

    entity_id: str
    translation_key: str
    is_credit: bool



@dataclass(slots=True)
class DashboardSelection:
    """Informations sur un tableau de bord énergie sélectionné."""

    identifier: str | None
    name: str | None
    preferences: dict[str, Any]
    device_consumption_totals: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConclusionSummary:
    """Résultat agrégé pour la conclusion du rapport."""

    production: float
    imported: float
    exported: float
    consumption: float
    charge: float
    discharge: float
    direct: float
    indirect: float | None
    total_estimated_consumption: float
    untracked_consumption: float
    has_battery: bool
    energy_unit: str | None
    formatted: Mapping[str, str]


def _recorder_metadata_requires_hass() -> bool:
    """Déterminer si recorder.get_metadata attend l'instance hass."""

    global _RECORDER_METADATA_REQUIRES_HASS

    if _RECORDER_METADATA_REQUIRES_HASS is None:
        try:
            parameters = inspect.signature(recorder_statistics.get_metadata).parameters
        except (TypeError, ValueError):
            _RECORDER_METADATA_REQUIRES_HASS = True
        else:
            _RECORDER_METADATA_REQUIRES_HASS = "hass" in parameters

    return _RECORDER_METADATA_REQUIRES_HASS


def _set_recorder_metadata_requires_hass(value: bool) -> None:
    """Mettre à jour le cache local de compatibilité recorder."""

    global _RECORDER_METADATA_REQUIRES_HASS
    _RECORDER_METADATA_REQUIRES_HASS = value


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialiser les structures de données du domaine."""

    hass.data.setdefault(DOMAIN, {})

    _async_register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurer une entrée de configuration."""

    domain_data = hass.data.setdefault(DOMAIN, {})

    domain_data[entry.entry_id] = entry

    entry.async_on_unload(entry.add_update_listener(update_listener))


    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Décharger l'intégration lors de la suppression de l'entrée."""

    domain_data = hass.data.get(DOMAIN)
    if not domain_data:
        return True

    domain_data.pop(entry.entry_id, None)

    if not _domain_has_config_entries(domain_data):
        hass.services.async_remove(DOMAIN, SERVICE_GENERATE_REPORT)
        domain_data.pop(DATA_SERVICES_REGISTERED, None)
        hass.data.pop(DOMAIN, None)

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Enregistrer les services si nécessaire."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_SERVICES_REGISTERED):
        return

    domain_data[DATA_SERVICES_REGISTERED] = True
    """Configurer le service de génération de rapport."""

    async def _async_generate(call: ServiceCall) -> None:
        await _async_handle_generate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_REPORT,
        _async_generate,
        schema=SERVICE_GENERATE_SCHEMA,
    )



async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recharger l'intégration lorsque les options sont mises à jour."""

    await hass.config_entries.async_reload(entry.entry_id)



CO2_SENSOR_CONFIG: tuple[tuple[str, str, bool, str], ...] = (
    (
        CONF_CO2_ELECTRICITY,
        "co2_electricity",
        False,
        DEFAULT_CO2_ELECTRICITY_SENSOR,
    ),
    (
        CONF_CO2_GAS,
        "co2_gas",
        False,
        DEFAULT_CO2_GAS_SENSOR,
    ),
    (
        CONF_CO2_WATER,
        "co2_water",
        False,
        DEFAULT_CO2_WATER_SENSOR,
    ),
    (
        CONF_CO2_SAVINGS,
        "co2_savings",
        True,
        DEFAULT_CO2_SAVINGS_SENSOR,
    ),
)


PRICE_SENSOR_CONFIG: tuple[tuple[str, str, bool, str], ...] = (
    (
        CONF_PRICE_ELECTRICITY_IMPORT,
        "price_electricity_import",
        False,
        DEFAULT_PRICE_ELECTRICITY_IMPORT_SENSOR,
    ),
    (
        CONF_PRICE_ELECTRICITY_EXPORT,
        "price_electricity_export",
        True,
        DEFAULT_PRICE_ELECTRICITY_EXPORT_SENSOR,
    ),
    (
        CONF_PRICE_GAS,
        "price_gas",
        False,
        DEFAULT_PRICE_GAS_SENSOR,
    ),
    (
        CONF_PRICE_WATER,
        "price_water",
        False,
        DEFAULT_PRICE_WATER_SENSOR,
    ),
)


_BASE_ALLOWED_OPTION_KEYS: tuple[str, ...] = (
    CONF_OUTPUT_DIR,
    CONF_FILENAME_PATTERN,
    CONF_DEFAULT_REPORT_TYPE,
    CONF_LANGUAGE,
    CONF_CO2,
    CONF_PRICE,
    CONF_CO2_ELECTRICITY,
    CONF_CO2_GAS,
    CONF_CO2_WATER,
    CONF_CO2_SAVINGS,
    CONF_OPENAI_API_KEY,
)

_ALLOWED_OPTION_KEYS: tuple[str, ...] = _BASE_ALLOWED_OPTION_KEYS + tuple(
    option_key for option_key, *_ in CO2_SENSOR_CONFIG + PRICE_SENSOR_CONFIG
)


def _build_co2_sensor_definitions(
    options: Mapping[str, Any]
) -> tuple[CO2SensorDefinition, ...]:
    """Return CO₂ sensor definitions, including user overrides."""

    if not bool(options.get(CONF_CO2, DEFAULT_CO2)):
        return ()

    definitions: list[CO2SensorDefinition] = []

    for option_key, translation_key, is_saving, _default_entity in CO2_SENSOR_CONFIG:
        override = options.get(option_key)
        if isinstance(override, str):
            override = override.strip()
        else:
            override = ""

        if not override:
            continue

        definitions.append(
            CO2SensorDefinition(override, translation_key, is_saving)
        )

    return tuple(definitions)


def _build_price_sensor_definitions(
    options: Mapping[str, Any]
) -> tuple[PriceSensorDefinition, ...]:
    """Return price sensor definitions, including user overrides."""

    if not bool(options.get(CONF_PRICE, DEFAULT_PRICE)):
        return ()

    definitions: list[PriceSensorDefinition] = []

    for option_key, translation_key, is_credit, _default_entity in PRICE_SENSOR_CONFIG:
        override = options.get(option_key)
        if isinstance(override, str):
            override = override.strip()
        else:
            override = ""

        if not override:
            continue

        definitions.append(
            PriceSensorDefinition(override, translation_key, is_credit)
        )

    return tuple(definitions)


def _get_config_entry_options(hass: HomeAssistant) -> dict[str, Any]:
    """Fusionner data et options des entrées actives."""

    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {}

    domain_data = hass.data.get(DOMAIN) or {}
    active_ids = _active_entry_ids(domain_data)

    options: dict[str, Any] = {}

    for entry in entries:
        if not active_ids or entry.entry_id in active_ids:
            # Fusion : entry.data = valeurs install, entry.options = modifs UI
            merged = {**(entry.data or {}), **(entry.options or {})}

            for key in _ALLOWED_OPTION_KEYS:
                if key in merged:
                    options[key] = merged[key]

            # Compatibilité ancienne version avec "period"
            if (
                CONF_DEFAULT_REPORT_TYPE not in options
                and CONF_PERIOD in merged
                and merged[CONF_PERIOD] in VALID_PERIODS
            ):
                options[CONF_DEFAULT_REPORT_TYPE] = merged[CONF_PERIOD]

    return options


def _active_entry_ids(domain_data: dict[str, Any]) -> set[str]:
    """Retourner les identifiants d'entrée actifs dans hass.data."""

    return {
        key

        for key, value in domain_data.items()
        if key != DATA_SERVICES_REGISTERED and isinstance(value, ConfigEntry)

    }


def _domain_has_config_entries(domain_data: dict[str, Any]) -> bool:
    """Déterminer s'il reste des entrées configurées dans hass.data."""

    return bool(_active_entry_ids(domain_data))


async def _async_handle_generate(hass: HomeAssistant, call: ServiceCall) -> None:
    """Exécuter la génération d'un rapport PDF."""

    manager = await async_get_manager(hass)


    options = _get_config_entry_options(hass)
    call_data = dict(call.data)

    dashboard_requested: str | None = call_data.get(CONF_DASHBOARD)


    option_report_type = options.get(CONF_DEFAULT_REPORT_TYPE)
    if option_report_type not in VALID_PERIODS:
        option_report_type = None


    period_value = call_data.get(CONF_PERIOD)
    if period_value not in VALID_PERIODS:
        period_value = option_report_type or DEFAULT_REPORT_TYPE

    period = str(period_value)
    call_data[CONF_PERIOD] = period

    start, end, display_start, display_end, bucket = _resolve_period(hass, call_data)

    selection = await _async_select_dashboard_preferences(
        hass,
        manager,
        dashboard_requested,
        start,
        end,
        bucket,
    )
    preferences = selection.preferences
    option_co2_enabled = bool(options.get(CONF_CO2, DEFAULT_CO2))
    option_price_enabled = bool(options.get(CONF_PRICE, DEFAULT_PRICE))

    co2_override = call.data.get(CONF_CO2)
    price_override = call.data.get(CONF_PRICE)

    co2_enabled = option_co2_enabled if co2_override is None else bool(co2_override)
    price_enabled = (
        option_price_enabled if price_override is None else bool(price_override)
    )

    metrics = _build_metrics(preferences, co2_enabled, price_enabled)
    cost_mapping = _build_cost_mapping(preferences)


    if not metrics:
        raise HomeAssistantError(
            "Aucune statistique n'a été trouvée dans les préférences énergie."
        )

    stats_map, metadata = await _collect_statistics(hass, metrics, start, end, bucket)
    totals = _calculate_totals(metrics, stats_map)

    if selection.device_consumption_totals:
        for metric in metrics:
            if metric.category != "Consommation appareils":
                continue
            normalized_total = selection.device_consumption_totals.get(
                metric.statistic_id
            )
            if normalized_total is None:
                continue
            totals[metric.statistic_id] = normalized_total
            metadata_entry = metadata.get(metric.statistic_id)
            if metadata_entry:
                metadata_entry[1]["unit_of_measurement"] = UnitOfEnergy.KILO_WATT_HOUR

    co2_definitions: list[CO2SensorDefinition] = []
    if co2_enabled:
        co2_definitions = _build_co2_sensor_definitions(options)

    price_definitions: list[PriceSensorDefinition] = []
    if price_enabled:
        price_definitions = _build_price_sensor_definitions(options)

    co2_totals: dict[str, float] = {}
    if co2_definitions:
        co2_totals = await _collect_co2_statistics(
            hass,
            start,
            end,
            co2_definitions,
        )

    price_totals: dict[str, float] = {}
    if price_definitions:
        price_totals = await _collect_price_statistics(
            hass,
            start,
            end,
            price_definitions,
        )

    output_dir_input = call.data.get(
        CONF_OUTPUT_DIR, options.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)
    )
    output_dir = Path(output_dir_input)
    if not output_dir.is_absolute():
        output_dir = Path(hass.config.path(output_dir_input))

    filename: str | None = call.data.get(CONF_FILENAME)
    filename_pattern: str = options.get(
        CONF_FILENAME_PATTERN, DEFAULT_FILENAME_PATTERN
    )
    if not isinstance(filename_pattern, str) or not filename_pattern.strip():
        filename_pattern = DEFAULT_FILENAME_PATTERN
    generated_at = dt_util.now()

    dashboard_label = _format_dashboard_label(selection)

    language = call.data.get(
        CONF_LANGUAGE, options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    )
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    translations = get_report_translations(language)

    conclusion_summary_for_advice = _prepare_conclusion_summary(
        metrics,
        totals,
        metadata,
    )
    conclusion_prompt_text = _compose_conclusion_prompt(
        translations, conclusion_summary_for_advice
    )

    raw_api_key = options.get(CONF_OPENAI_API_KEY)
    api_key: str | None
    if isinstance(raw_api_key, str):
        api_key = raw_api_key.strip() or None
    else:
        api_key = None

    advice_text = await generate_advice(
        conclusion_prompt_text,
        api_key,
        translations.language,
    )

    pdf_path = await hass.async_add_executor_job(
        _build_pdf,
        metrics,
        totals,
        metadata,
        cost_mapping,
        display_start,
        display_end,
        bucket,
        output_dir,
        filename,
        filename_pattern,
        generated_at,
        dashboard_label,

        period,

        translations,

        co2_definitions,
        co2_totals,

        price_definitions,
        price_totals,

        advice_text,
        conclusion_summary_for_advice,
    )

    message_lines = [
        translations.notification_line_period.format(
            start=display_start.date().isoformat(),
            end=display_end.date().isoformat(),
        )
    ]

    if dashboard_label:
        message_lines.append(
            translations.notification_line_dashboard.format(
                dashboard=dashboard_label
            )
        )

    message_lines.append(translations.notification_line_file.format(path=pdf_path))
    message = "\n".join(message_lines)
    persistent_notification.async_create(
        hass,
        message,
        title=translations.notification_title,
        notification_id=f"{DOMAIN}_last_report",
    )
    if dashboard_label:
        _LOGGER.info(
            "Rapport %s généré (%s): %s",
            translations.language,
            dashboard_label,
            pdf_path,
        )
    else:
        _LOGGER.info("Rapport %s généré: %s", translations.language, pdf_path)


async def _async_select_dashboard_preferences(
    hass: HomeAssistant,
    manager: Any,
    requested_dashboard: str | None,
    start: datetime,
    end: datetime,
    bucket: str,
) -> DashboardSelection:
    """Sélectionner les préférences énergie pour le tableau demandé."""

    dashboards = _collect_dashboard_preferences(manager)


    if requested_dashboard:
        normalized = _normalize_dashboard_key(requested_dashboard)

        if normalized is not None:
            for selection in dashboards:
                if _match_dashboard_key(selection, normalized):
                    return await _async_enrich_selection_with_device_totals(
                        hass, manager, selection, start, end, bucket
                    )

        fetched = await _async_fetch_dashboard_preferences_via_methods(
            hass, manager, requested_dashboard
        )
        if fetched:
            return await _async_enrich_selection_with_device_totals(
                hass, manager, fetched, start, end, bucket
            )

        raise HomeAssistantError(
            f"Aucun tableau de bord énergie nommé '{requested_dashboard}' n'a été trouvé."
        )


    if dashboards:
        selection = _pick_default_dashboard(manager, dashboards)
        return await _async_enrich_selection_with_device_totals(
            hass, manager, selection, start, end, bucket
        )

    data = getattr(manager, "data", None)
    if _is_energy_preferences(data):
        selection = DashboardSelection(None, None, data)
        return await _async_enrich_selection_with_device_totals(
            hass, manager, selection, start, end, bucket
        )

    raise HomeAssistantError(
        "Le tableau de bord énergie n'est pas encore configuré."
    )


async def _async_enrich_selection_with_device_totals(
    _hass: HomeAssistant,
    manager: Any,
    selection: DashboardSelection,
    start: datetime,
    end: datetime,
    bucket: str,
) -> DashboardSelection:
    """Compléter une sélection avec les totaux normalisés du tableau énergie."""

    totals = await _async_get_dashboard_device_consumption_totals(
        manager, selection.preferences, start, end, bucket
    )
    selection.device_consumption_totals = totals
    return selection


async def _async_get_dashboard_device_consumption_totals(
    manager: Any,
    preferences: Mapping[str, Any],
    start: datetime,
    end: datetime,
    bucket: str,
) -> dict[str, float]:
    """Récupérer les totaux en kWh pour la consommation des appareils."""

    device_entries = preferences.get("device_consumption", [])
    if not isinstance(device_entries, list):
        return {}

    statistic_ids: list[str] = []
    for entry in device_entries:
        if not isinstance(entry, dict):
            continue
        statistic_id = entry.get("stat_consumption")
        if not statistic_id:
            continue
        if statistic_id not in statistic_ids:
            statistic_ids.append(str(statistic_id))

    if not statistic_ids:
        return {}

    totals: dict[str, float] = {}
    remaining: set[str] = set(statistic_ids)

    if manager is None:
        return totals

    relevant_roots = _collect_dashboard_statistics_roots(manager)

    def _parse_datetime_like(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                return datetime.fromtimestamp(value, tz=dt_util.UTC)
            except (OSError, OverflowError, ValueError):
                return None
        if isinstance(value, str):
            parsed = dt_util.parse_datetime(value)
            if parsed is not None:
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=dt_util.UTC)
                return parsed
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return None
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt_util.UTC)
            return parsed
        return None

    def _period_matches(mapping: Mapping[str, Any]) -> bool:
        candidate_bucket = mapping.get("bucket") or mapping.get("period") or mapping.get(
            "granularity"
        )
        if isinstance(candidate_bucket, str) and candidate_bucket:
            if candidate_bucket.lower() != bucket.lower():
                return False

        tolerance = timedelta(minutes=5)
        for key, reference in (("start", start), ("end", end)):
            candidate = mapping.get(key) or mapping.get(f"{key}_time") or mapping.get(
                f"{key}_at"
            )
            if candidate is None:
                continue
            parsed = _parse_datetime_like(candidate)
            if parsed is None:
                continue
            if abs((dt_util.as_utc(parsed) - dt_util.as_utc(reference)).total_seconds()) > tolerance.total_seconds():
                return False

        return True

    def _sum_changes(rows: Any) -> float | None:
        if not isinstance(rows, list):
            return None
        total = 0.0
        found = False
        for row in rows:
            value: float | None = None
            if isinstance(row, Mapping):
                for key in ("change", "delta", "value", "kwh", "energy", "sum"):
                    candidate = row.get(key)
                    if isinstance(candidate, (int, float, Decimal)) and not isinstance(
                        candidate, bool
                    ):
                        value = float(candidate)
                        break
            elif isinstance(row, (int, float, Decimal)) and not isinstance(row, bool):
                value = float(row)

            if value is None:
                continue
            total += value
            found = True

        return total if found else None

    def _coerce_total(candidate: Any) -> float | None:
        if isinstance(candidate, (int, float, Decimal)) and not isinstance(candidate, bool):
            return float(candidate)

        if isinstance(candidate, Mapping):
            # direct numeric keys
            for key in (
                "total",
                "total_kwh",
                "total_consumption",
                "kwh",
                "energy",
                "energy_kwh",
                "value",
                "sum",
                "change",
                "delta",
                "consumption",
            ):
                value = candidate.get(key)
                if isinstance(value, (int, float, Decimal)) and not isinstance(
                    value, bool
                ):
                    return float(value)

            for key in ("statistics", "stats", "data", "entries", "rows", "points"):
                nested = candidate.get(key)
                total = _sum_changes(nested)
                if total is not None:
                    return total

        if isinstance(candidate, list):
            total = _sum_changes(candidate)
            if total is not None:
                return total

        return None

    relevant_keys = {
        "device_consumption_totals",
        "device_consumption",
        "statistics",
        "stats",
        "by_statistic_id",
        "statistics_by_statistic_id",
        "totals",
        "total",
        "data",
        "result",
        "results",
        "consumption",
        "devices",
        "metrics",
        "values",
        "normalized",
        "normalized_totals",
        "normalized_statistics",
    }

    visited: set[int] = set()

    def _process_mapping(mapping: Mapping[str, Any]) -> None:
        if not remaining:
            return

        if not _period_matches(mapping):
            return

        if "statistic_id" in mapping:
            statistic_id = mapping.get("statistic_id")
            if statistic_id is not None:
                stat_key = str(statistic_id)
                if stat_key in remaining:
                    total = _coerce_total(mapping)
                    if total is None:
                        total = _sum_changes(mapping.get("statistics"))
                    if total is not None:
                        totals[stat_key] = total
                        remaining.discard(stat_key)

        for stat_key in list(remaining):
            if stat_key not in mapping:
                continue
            total = _coerce_total(mapping.get(stat_key))
            if total is not None:
                totals[stat_key] = total
                remaining.discard(stat_key)

        for value in mapping.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if not isinstance(item, Mapping):
                    continue
                candidate_stat = item.get("statistic_id") or item.get("stat_consumption")
                if candidate_stat is None:
                    continue
                stat_key = str(candidate_stat)
                if stat_key not in remaining:
                    continue
                total = _coerce_total(item)
                if total is None:
                    total = _sum_changes(item.get("statistics"))
                if total is None:
                    continue
                totals[stat_key] = total
                remaining.discard(stat_key)
                if not remaining:
                    return

        for key in relevant_keys:
            if key not in mapping:
                continue
            value = mapping.get(key)
            if isinstance(value, Mapping):
                _search_structure(value)
            elif isinstance(value, list):
                for item in value:
                    _search_structure(item)

    def _search_structure(candidate: Any, depth: int = 0) -> None:
        if not remaining or depth > 8:
            return

        if isinstance(candidate, Mapping):
            obj_id = id(candidate)
            if obj_id in visited:
                return
            visited.add(obj_id)
            _process_mapping(candidate)
            if not remaining:
                return
            for value in candidate.values():
                if isinstance(value, (Mapping, list, tuple, set)):
                    _search_structure(value, depth + 1)
            return

        if isinstance(candidate, (list, tuple, set)):
            obj_id = id(candidate)
            if obj_id in visited:
                return
            visited.add(obj_id)
            for item in candidate:
                if not remaining:
                    break
                if isinstance(item, (Mapping, list, tuple, set)):
                    _search_structure(item, depth + 1)
            return

    for root in relevant_roots:
        _search_structure(root)
        if not remaining:
            break

    return totals


def _collect_dashboard_statistics_roots(manager: Any) -> list[Any]:
    """Collect the potential statistics containers exposed by the energy manager."""

    roots: list[Any] = []
    seen_ids: set[int] = set()

    def _add_candidate(candidate: Any) -> None:
        if isinstance(candidate, (Mapping, list, tuple, set)):
            obj_id = id(candidate)
            if obj_id in seen_ids:
                return
            seen_ids.add(obj_id)
            roots.append(candidate)

    if manager is None:
        return roots

    attributes = {
        "data",
        "dashboards",
        "dashboard",
        "statistics",
        "stats",
        "result",
        "results",
        "consumption",
        "device_consumption",
        "normalized",
    }

    for attr in attributes:
        if not hasattr(manager, attr):
            continue
        value = getattr(manager, attr)
        if value is None:
            continue
        _add_candidate(value)
        if hasattr(value, "data"):
            _add_candidate(getattr(value, "data"))

        if isinstance(value, Mapping):
            for key in attributes:
                nested = value.get(key)
                if nested is not None:
                    _add_candidate(nested)

    coordinator = getattr(manager, "coordinator", None)
    if coordinator is not None:
        _add_candidate(getattr(coordinator, "data", None))
        _add_candidate(coordinator)

    coordinators = getattr(manager, "coordinators", None)
    if isinstance(coordinators, Mapping):
        for item in coordinators.values():
            if item is None:
                continue
            _add_candidate(item)
            _add_candidate(getattr(item, "data", None))

    if isinstance(manager, Mapping):
        _add_candidate(manager)

    try:
        manager_vars = vars(manager)
    except TypeError:
        manager_vars = {}

    for attr, value in manager_vars.items():
        if attr.startswith("_") or "hass" in attr:
            continue
        _add_candidate(value)
        if hasattr(value, "data"):
            _add_candidate(getattr(value, "data", None))

    return roots


def _collect_dashboard_preferences(manager: Any) -> list[DashboardSelection]:
    """Extraire les différents tableaux de bord disponibles."""

    selections: list[DashboardSelection] = []

    selections.extend(_extract_named_preferences(getattr(manager, "data", None)))

    for attr in ("dashboards", "dashboard"):
        if hasattr(manager, attr):
            selections.extend(_extract_named_preferences(getattr(manager, attr)))

    data = getattr(manager, "data", None)
    if isinstance(data, dict):
        for key in ("dashboards", "dashboard"):
            if key in data:
                selections.extend(_extract_named_preferences(data[key]))

    deduped: list[DashboardSelection] = []
    for selection in selections:
        if not _is_energy_preferences(selection.preferences):
            continue

        key = (selection.identifier, selection.name)
        existing_index = next(
            (index for index, current in enumerate(deduped) if (current.identifier, current.name) == key),
            None,
        )

        if existing_index is None:
            deduped.append(selection)
            continue

        current = deduped[existing_index]
        replace = False
        if current.identifier is None and selection.identifier is not None:
            replace = True
        elif current.name is None and selection.name is not None:
            replace = True

        if replace:
            deduped[existing_index] = selection

    return deduped


def _extract_named_preferences(
    candidate: Any, fallback_id: str | None = None, fallback_name: str | None = None
) -> list[DashboardSelection]:
    """Parcourir récursivement une structure pour trouver des préférences énergie."""

    selections: list[DashboardSelection] = []

    def _add(preferences: Any, identifier: str | None, name: str | None) -> None:
        if _is_energy_preferences(preferences):
            selections.append(
                DashboardSelection(
                    identifier if identifier else fallback_id,
                    name if name else fallback_name,
                    preferences,
                )
            )

    if candidate is None:
        return selections

    if _is_energy_preferences(candidate):
        _add(candidate, fallback_id, fallback_name)
        return selections

    if isinstance(candidate, dict):
        current_id = fallback_id
        for key in ("dashboard_id", "id", "slug", "key"):
            if key in candidate and candidate[key] is not None:
                value = candidate[key]
                current_id = str(value)
                break

        current_name = fallback_name
        for key in ("name", "title", "label"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                current_name = value
                break

        if "preferences" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["preferences"], current_id, current_name)
            )
        if "dashboards" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["dashboards"], current_id, current_name)
            )
        if "dashboard" in candidate:
            selections.extend(
                _extract_named_preferences(candidate["dashboard"], current_id, current_name)
            )

        for key, value in candidate.items():
            if key in {"preferences", "dashboards", "dashboard", "energy_sources", "device_consumption"}:
                continue
            if isinstance(value, (dict, list)):
                next_id = current_id
                if isinstance(key, str) and key not in {"name", "title", "label"}:
                    next_id = key
                selections.extend(_extract_named_preferences(value, next_id, current_name))

        return selections

    if isinstance(candidate, list):
        for item in candidate:
            selections.extend(_extract_named_preferences(item, fallback_id, fallback_name))
        return selections

    for attr in ("preferences", "data"):
        if hasattr(candidate, attr):
            sub_candidate = getattr(candidate, attr)
            current_id = fallback_id
            for attr_key in ("dashboard_id", "id", "slug", "key"):
                if hasattr(candidate, attr_key):
                    value = getattr(candidate, attr_key)
                    if value is not None:
                        current_id = str(value)
                        break

            current_name = fallback_name
            for attr_name in ("name", "title", "label"):
                if hasattr(candidate, attr_name):
                    value = getattr(candidate, attr_name)
                    if isinstance(value, str) and value.strip():
                        current_name = value
                        break

            selections.extend(
                _extract_named_preferences(sub_candidate, current_id, current_name)
            )
            break

    return selections


def _is_energy_preferences(candidate: Any) -> bool:
    """Vérifier qu'une structure correspond aux préférences énergie attendues."""

    return (
        isinstance(candidate, dict)
        and "energy_sources" in candidate
        and "device_consumption" in candidate
    )


def _normalize_dashboard_key(value: str | None) -> str | None:
    """Normaliser un identifiant de tableau de bord pour comparaison."""

    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None

    return normalized.casefold()


def _match_dashboard_key(selection: DashboardSelection, requested: str) -> bool:
    """Comparer un tableau de bord à une clé normalisée."""

    for candidate in (selection.identifier, selection.name):
        normalized = _normalize_dashboard_key(candidate)
        if normalized and normalized == requested:
            return True

    return False


def _pick_default_dashboard(
    manager: Any, dashboards: list[DashboardSelection]
) -> DashboardSelection:
    """Choisir un tableau par défaut parmi ceux disponibles."""

    def _find_match(value: Any) -> DashboardSelection | None:
        normalized = _normalize_dashboard_key(value if value is None else str(value))
        if not normalized:
            return None
        for item in dashboards:
            if _match_dashboard_key(item, normalized):
                return item
        return None

    data = getattr(manager, "data", None)
    if isinstance(data, dict):
        for key in ("selected_dashboard", "default_dashboard", "active_dashboard"):
            selection = _find_match(data.get(key))
            if selection:
                return selection


    for attr in ("selected_dashboard", "default_dashboard", "active_dashboard"):
        if hasattr(manager, attr):
            selection = _find_match(getattr(manager, attr))
            if selection:
                return selection


    return dashboards[0]


async def _async_fetch_dashboard_preferences_via_methods(
    hass: HomeAssistant, manager: Any, dashboard_id: str
) -> DashboardSelection | None:
    """Tenter de récupérer les préférences via les méthodes du gestionnaire."""

    method_names = (
        "async_get_dashboard",
        "async_get_dashboard_preferences",
        "async_get_dashboard_by_id",
        "async_get_dashboard_by_slug",
        "get_dashboard",
    )

    for name in method_names:
        method = getattr(manager, name, None)
        if not callable(method):
            continue

        for args in ((dashboard_id,), (hass, dashboard_id)):
            try:
                result = method(*args)
            except TypeError:
                continue
            except Exception as err:  # pragma: no cover - best effort logging
                _LOGGER.debug(
                    "Erreur lors de l'appel de %s pour récupérer le tableau '%s': %s",
                    name,
                    dashboard_id,
                    err,
                )
                continue

            result = await _await_if_needed(result)

            selections = _extract_named_preferences(result, dashboard_id)
            if selections:
                requested = _normalize_dashboard_key(dashboard_id)
                if requested:
                    for selection in selections:
                        if _match_dashboard_key(selection, requested):
                            if selection.identifier is None:
                                return DashboardSelection(
                                    dashboard_id, selection.name, selection.preferences
                                )
                            return selection

                primary = selections[0]
                if primary.identifier is None:
                    return DashboardSelection(dashboard_id, primary.name, primary.preferences)
                return primary

            if _is_energy_preferences(result):
                return DashboardSelection(dashboard_id, None, result)

    return None



async def _await_if_needed(result: Any) -> Any:
    """Attendre une valeur si elle est awaitable."""

    if inspect.isawaitable(result):
        return await result
    return result


def _format_dashboard_label(selection: DashboardSelection) -> str | None:
    """Créer une étiquette lisible pour le tableau sélectionné."""

    name = selection.name
    identifier = selection.identifier

    if name and identifier:
        if _normalize_dashboard_key(name) == _normalize_dashboard_key(identifier):
            return name
        return f"{name} ({identifier})"

    return name or identifier



def _resolve_period(
    hass: HomeAssistant, call_data: dict[str, Any]
) -> tuple[datetime, datetime, datetime, datetime, str]:
    """Calculer les dates de début et fin en tenant compte de la granularité."""

    period: str = call_data.get(CONF_PERIOD, DEFAULT_PERIOD)
    start_date = _coerce_service_date(call_data.get(CONF_START_DATE), CONF_START_DATE)
    end_date = _coerce_service_date(call_data.get(CONF_END_DATE), CONF_END_DATE)

    now_local = dt_util.now()

    if start_date is None:
        if period == "day":
            start_date = now_local.date()
        elif period == "week":
            start_date = (now_local - timedelta(days=now_local.weekday())).date()
        elif period == "month":
            start_date = now_local.replace(day=1).date()
        else:
            raise HomeAssistantError("Période non supportée")

    if end_date is None:
        if period == "day":
            end_date = start_date
        elif period == "week":
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            _, last_day = calendar.monthrange(start_date.year, start_date.month)
            end_date = start_date.replace(day=last_day)
    if end_date is None:
        end_date = start_date

    if end_date < start_date:
        raise HomeAssistantError("La date de fin doit être postérieure à la date de début.")

    timezone = _select_timezone(hass)

    start_local = _localize_date(start_date, timezone)

    # ``end_date`` reste inclusif comme dans le tableau de bord Énergie ;
    # recorder se charge ensuite de convertir ce point de sortie en borne exclusive.
    end_local = _localize_date(end_date, timezone)
    end_local_exclusive = end_local + timedelta(days=1)

    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local_exclusive)  # ⚠️ utiliser la borne exclusive
    display_end = end_local_exclusive - timedelta(seconds=1)

    return (
        start_utc,
        end_utc,
        start_local,
        display_end,
        _select_bucket(period, start_local, end_local_exclusive),
    )




def _coerce_service_date(value: Any, field: str) -> date | None:
    """Convertir une valeur issue du service en date."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        parsed = dt_util.parse_date(value)
        if parsed is not None:
            return parsed

    raise HomeAssistantError(
        f"Impossible d'interpréter {field} comme une date valide (format attendu YYYY-MM-DD)."
    )


def _select_timezone(hass: HomeAssistant) -> tzinfo:
    """Déterminer le fuseau horaire à utiliser pour les conversions locales."""

    if hass.config.time_zone:
        timezone = dt_util.get_time_zone(hass.config.time_zone)
        if timezone is not None:
            return timezone

    return dt_util.DEFAULT_TIME_ZONE


def _select_bucket(period: str, start_local: datetime, end_local_exclusive: datetime) -> str:
    """Choisir une granularité compatible avec recorder pour la période demandée."""

    normalized = period.lower() if isinstance(period, str) else ""

    if normalized == "day":
        return "hour"

    if normalized == "week":
        return "day"

    if normalized == "month":
        return "day"

    span = end_local_exclusive - start_local

    if span <= timedelta(days=2):
        return "hour"

    if span <= timedelta(days=35):
        return "day"

    return "month"


def _localize_date(day: date, timezone: tzinfo) -> datetime:
    """Assembler une date locale en tenant compte des transitions horaires."""

    naive = datetime.combine(day, time.min)
    localize = getattr(timezone, "localize", None)
    if callable(localize):  # pytz support
        return localize(naive)
    return naive.replace(tzinfo=timezone)



def _build_metrics(
    preferences: "EnergyPreferences" | dict[str, Any],
    co2_enabled: bool = False,
    price_enabled: bool = False,
) -> list[MetricDefinition]:
    """Lister les statistiques à inclure dans le rapport."""

    metrics: list[MetricDefinition] = []
    seen: set[str] = set()

    def _add(statistic_id: str | None, category: str) -> None:
        if not statistic_id or statistic_id in seen:
            return
        seen.add(statistic_id)
        metrics.append(MetricDefinition(category, statistic_id))

    def _add_co2_stat(container: Any) -> None:
        if not co2_enabled or not isinstance(container, dict):
            return
        _add(container.get("stat_co2"), "Émissions CO₂")

    for source in preferences.get("energy_sources", []):
        source_type = source.get("type")
        if source_type == "grid":
            for flow in source.get("flow_from", []):
                _add(flow.get("stat_energy_from"), "Import réseau")
                _add(flow.get("stat_cost"), "Coût réseau")
                _add_co2_stat(flow)
            for flow in source.get("flow_to", []):
                _add(flow.get("stat_energy_to"), "Export réseau")
                _add(flow.get("stat_compensation"), "Compensation réseau")
                _add_co2_stat(flow)
        elif source_type == "solar":
            _add(source.get("stat_energy_from"), "Production solaire")
        elif source_type == "battery":
            _add(source.get("stat_energy_from"), "Décharge batterie")
            _add(source.get("stat_energy_to"), "Charge batterie")
        elif source_type == "gas":
            _add(source.get("stat_energy_from"), "Consommation gaz")
            _add(source.get("stat_cost"), "Coût gaz")
        elif source_type == "water":
            _add(source.get("stat_energy_from"), "Consommation eau")
            _add(source.get("stat_cost"), "Coût eau")

        _add_co2_stat(source)

    for device in preferences.get("device_consumption", []):
        _add(device.get("stat_consumption"), "Consommation appareils")
        _add_co2_stat(device)

    return metrics


def _build_cost_mapping(
    preferences: "EnergyPreferences" | dict[str, Any]
) -> dict[str, str]:
    """Associer chaque statistique d'énergie à sa statistique de coût."""

    mapping: dict[str, str] = {}

    def _link(energy_stat: str | None, cost_stat: str | None) -> None:
        if not energy_stat or not cost_stat:
            return
        mapping.setdefault(energy_stat, cost_stat)

    for source in preferences.get("energy_sources", []):
        if not isinstance(source, dict):
            continue

        source_type = source.get("type")

        if source_type == "grid":
            for flow in source.get("flow_from", []):
                if isinstance(flow, dict):
                    _link(flow.get("stat_energy_from"), flow.get("stat_cost"))
            for flow in source.get("flow_to", []):
                if isinstance(flow, dict):
                    _link(
                        flow.get("stat_energy_to"),
                        flow.get("stat_compensation"),
                    )
        else:
            _link(source.get("stat_energy_from"), source.get("stat_cost"))

    for device in preferences.get("device_consumption", []):
        if isinstance(device, dict):
            _link(device.get("stat_consumption"), device.get("stat_cost"))

    return mapping


async def _collect_statistics(
    hass: HomeAssistant,
    metrics: Iterable[MetricDefinition],
    start: datetime,
    end: datetime,
    bucket: str,
) -> tuple[dict[str, list[StatisticsRow]], dict[str, tuple[int, StatisticMetaData]]]:
    """Récupérer les statistiques depuis recorder."""

    statistic_ids = {metric.statistic_id for metric in metrics}
    if not statistic_ids:
        return {}, {}

    try:
        instance = recorder.get_instance(hass)
    except RuntimeError as err:
        raise HomeAssistantError(
            "Le composant recorder doit être actif pour générer le rapport."
        ) from err

    metadata_requires_hass = _recorder_metadata_requires_hass()
    metadata: dict[str, tuple[int, StatisticMetaData]]

    try:
        if metadata_requires_hass:
            metadata = await instance.async_add_executor_job(
                _get_recorder_metadata_with_hass,
                hass,
                statistic_ids,
            )
        else:
            metadata = await instance.async_add_executor_job(
                recorder_statistics.get_metadata,
                statistic_ids,
            )
    except TypeError as err:
        err_message = str(err)

        if metadata_requires_hass and _metadata_error_indicates_legacy_signature(err_message):
            _LOGGER.debug(
                "Recorder get_metadata ne supporte pas hass en argument, bascule sur la signature héritée: %s",
                err_message,
            )
            _set_recorder_metadata_requires_hass(False)
            metadata = await instance.async_add_executor_job(
                recorder_statistics.get_metadata,
                statistic_ids,
            )
        elif (
            not metadata_requires_hass
            and _metadata_error_indicates_requires_hass(err_message)
        ):
            _LOGGER.debug(
                "Recorder get_metadata nécessite hass, nouvelle tentative avec la signature actuelle: %s",
                err_message,
            )
            _set_recorder_metadata_requires_hass(True)
            metadata = await instance.async_add_executor_job(
                _get_recorder_metadata_with_hass,
                hass,
                statistic_ids,
            )
        else:
            raise


    entity_registry = er.async_get(hass)
    states = hass.states

    for statistic_id in statistic_ids:
        entry = metadata.get(statistic_id)
        if not entry:
            continue

        meta = entry[1]

        current_name = meta.get("name")
        current_name_str = str(current_name).strip() if current_name is not None else ""
        if current_name_str and current_name_str != statistic_id:
            continue

        friendly_name: str | None = None

        state = states.get(statistic_id)
        if state and state.name and state.name.strip():
            friendly_name = state.name.strip()
        else:
            registry_entry = entity_registry.async_get(statistic_id)
            if registry_entry:
                registry_name = registry_entry.name or registry_entry.original_name
                if registry_name:
                    friendly_name = str(registry_name).strip()

        if friendly_name:
            meta["name"] = friendly_name

    stats_map = await instance.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        end,
        statistic_ids,
        bucket,
        None,
        {"change"},
    )

    return stats_map, metadata


async def _collect_co2_statistics(
    hass: HomeAssistant,
    start: datetime,
    end: datetime,
    sensors: Iterable[CO2SensorDefinition],
) -> dict[str, float]:
    """Assembler les totaux CO₂ sur la période demandée."""

    definitions = list(sensors)
    results: dict[str, float] = {
        definition.translation_key: 0.0 for definition in definitions
    }

    if not definitions:
        return results

    entity_map = {definition.entity_id: definition for definition in definitions}
    statistic_ids = list(entity_map)

    instance = recorder.get_instance(hass)

    stats_map = await instance.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        end,
        statistic_ids,
        "day",
        None,
        {"change"},
    )

    for entity_id in statistic_ids:
        rows = stats_map.get(entity_id)
        if not rows:
            continue

        total = 0.0
        has_sum = False
        for row in rows:
            change_value = row.get("change")
            if change_value is None:
                continue
            has_sum = True
            total += float(change_value)

        if has_sum:
            definition = entity_map[entity_id]
            results[definition.translation_key] = total

    return results


async def _collect_price_statistics(
    hass: HomeAssistant,
    start: datetime,
    end: datetime,
    sensors: Iterable[PriceSensorDefinition],
) -> dict[str, float]:
    """Assembler les totaux financiers sur la période demandée."""

    definitions = list(sensors)
    results: dict[str, float] = {
        definition.translation_key: 0.0 for definition in definitions
    }

    if not definitions:
        return results

    entity_map = {definition.entity_id: definition for definition in definitions}
    statistic_ids = list(entity_map)

    instance = recorder.get_instance(hass)

    stats_map = await instance.async_add_executor_job(
        recorder_statistics.statistics_during_period,
        hass,
        start,
        end,
        statistic_ids,
        "day",
        None,
        {"change"},
    )

    for entity_id in statistic_ids:
        rows = stats_map.get(entity_id)
        if not rows:
            continue

        total = 0.0
        has_sum = False
        for row in rows:
            change_value = row.get("change")
            if change_value is None:
                continue
            has_sum = True
            total += float(change_value)

        if has_sum:
            definition = entity_map[entity_id]
            results[definition.translation_key] = total

    return results


def _get_recorder_metadata_with_hass(
    hass: HomeAssistant,
    statistic_ids: set[str],
) -> dict[str, tuple[int, StatisticMetaData]]:
    """Appeler get_metadata avec hass en argument mot-clé."""

    return recorder_statistics.get_metadata(hass, statistic_ids=statistic_ids)


def _metadata_error_indicates_legacy_signature(message: str) -> bool:
    """Détecter les erreurs indiquant l'ancienne signature de get_metadata."""

    lowered = message.lower()
    return any(
        hint in lowered
        for hint in (
            "multiple values",
            "positional argument",
            "unexpected keyword",
        )
    )


def _metadata_error_indicates_requires_hass(message: str) -> bool:
    """Détecter les erreurs montrant que hass est requis."""

    lowered = message.lower()
    return any(
        hint in lowered
        for hint in (
            "missing 1 required positional argument",
            "unhashable type",
            "homeassistant",
        )
    )


def _calculate_totals(
    metrics: Iterable[MetricDefinition],
    stats: dict[str, list[StatisticsRow]],
) -> dict[str, float]:
    """Additionner les valeurs sur la période pour chaque statistique."""

    totals: dict[str, float] = {metric.statistic_id: 0.0 for metric in metrics}

    for statistic_id, rows in stats.items():
        if not rows:
            continue


        change_total = 0.0
        has_change = False

        for row in rows:

            change_value = row.get("change")
            if change_value is None:
                continue
            has_change = True
            change_total += float(change_value)

        if has_change:
            totals[statistic_id] = change_total


    return totals


def _discover_logo_candidate(output_dir: Path) -> Path | None:
    """Rechercher un logo optionnel à intégrer dans la page de garde."""

    candidates: list[Path] = []
    search_dirs = {output_dir, Path(__file__).resolve().parent}

    parent = output_dir.parent
    if parent != output_dir:
        search_dirs.add(parent)

    for directory in search_dirs:
        for filename in ("logo.png", "logo.jpg", "logo.jpeg"):
            candidate = directory / filename
            if candidate.exists():
                candidates.append(candidate)

    return candidates[0] if candidates else None


def _build_pdf(
    metrics: list[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
    cost_mapping: Mapping[str, str],
    display_start: datetime,
    display_end: datetime,
    bucket: str,
    output_dir: Path,
    filename: str | None,
    filename_pattern: str,
    generated_at: datetime,
    dashboard_label: str | None,

    period: str,

    translations: ReportTranslations,

    co2_definitions: Iterable[CO2SensorDefinition],
    co2_totals: dict[str, float],

    price_definitions: Iterable[PriceSensorDefinition],
    price_totals: dict[str, float],

    advice_text: str,
    conclusion_summary: ConclusionSummary | None = None,

) -> str:
    """Assembler le PDF et le sauvegarder sur disque."""

    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        filename = filename.strip()
        if not filename:
            filename = None

    if not filename:
        context = {
            "start": display_start.date().isoformat(),
            "end": display_end.date().isoformat(),
            "period": period,
        }

        try:
            filename = filename_pattern.format(**context)
        except KeyError as err:
            raise HomeAssistantError(
                "Le modèle de nom de fichier contient un espace réservé inconnu: "
                f"{err.args[0]}"
            ) from err

        filename = filename.strip()

        if not filename:
            raise HomeAssistantError(
                "Le modèle de nom de fichier a généré un nom vide."
            )
    elif not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    file_path = output_dir / filename

    period_label = f"{display_start.strftime('%d/%m/%Y')} → {display_end.strftime('%d/%m/%Y')}"

    bucket_label = translations.bucket_labels.get(bucket, bucket)
    logo_path = _discover_logo_candidate(output_dir)
    subtitle = translations.cover_subtitle.format(
        start=display_start.strftime("%d/%m/%Y"),
        end=display_end.strftime("%d/%m/%Y"),
    )
    builder = EnergyPDFBuilder(
        translations.pdf_title,
        period_label=period_label,
        generated_at=generated_at,
        translations=translations,

        logo_path=logo_path,
    )

    co2_definitions = tuple(co2_definitions)
    price_definitions = tuple(price_definitions)

    cover_details = [

        translations.cover_period.format(period=period_label),
        translations.cover_bucket.format(bucket=bucket_label),
        translations.cover_stats.format(count=len(metrics)),
        translations.cover_generated.format(
            timestamp=generated_at.strftime("%d/%m/%Y %H:%M")
        ),
    ]
    if dashboard_label:
        cover_details.insert(
            1, translations.cover_dashboard.format(dashboard=dashboard_label)
        )

    builder.add_cover_page(subtitle=subtitle, details=cover_details)

    builder.add_section_title(translations.summary_title)
    builder.add_paragraph(translations.summary_intro)


    summary_rows, summary_series = _prepare_summary_rows(metrics, totals, metadata)
    if conclusion_summary is None:
        conclusion_summary = _prepare_conclusion_summary(
            metrics,
            totals,
            metadata,
        )

    summary_display_rows = list(summary_rows)
    summary_emphasize_rows: list[int] = list(range(len(summary_display_rows)))

    if conclusion_summary:
        energy_unit = conclusion_summary.energy_unit or ""

        summary_display_rows = [
            (
                translations.summary_row_total_consumption_label,
                _format_number(
                    conclusion_summary.total_estimated_consumption
                ),
                energy_unit,
            ),
            *summary_rows,
            (
                translations.summary_row_untracked_consumption_label,
                _format_number(conclusion_summary.untracked_consumption),
                energy_unit,
            ),
        ]
        summary_emphasize_rows = [0, len(summary_display_rows) - 1]

    summary_widths = builder.compute_column_widths((0.55, 0.27, 0.18))
    builder.add_table(
        TableConfig(
            title=translations.summary_table_title,
            headers=translations.summary_headers,
            rows=summary_display_rows,
            column_widths=summary_widths,
            emphasize_rows=summary_emphasize_rows,

            first_column_is_category=True,
        )
    )

    builder.add_paragraph(translations.summary_note_totals)
    builder.add_paragraph(translations.summary_note_negative)

    builder.add_section_title(translations.detail_title)
    builder.add_paragraph(translations.detail_intro)


    detail_rows = _prepare_detail_rows(
        metrics,
        totals,
        metadata,
        cost_mapping,
    )
    detail_widths = builder.compute_column_widths((0.25, 0.51, 0.14, 0.10))
    builder.add_table(
        TableConfig(
            title=translations.detail_table_title,
            headers=translations.detail_headers,
            rows=detail_rows,
            column_widths=detail_widths,
            first_column_is_category=True,
        )
    )

    if summary_series:

        builder.add_paragraph(translations.chart_intro)
        builder.add_chart(translations.chart_title, summary_series)


    if price_definitions:
        price_totals_map = price_totals or {}
        builder.add_section_title(translations.price_section_title)
        builder.add_paragraph(translations.price_section_intro)

        price_rows: list[tuple[str, str, str]] = []
        expenses_total = 0.0
        income_total = 0.0

        for definition in price_definitions:
            value = price_totals_map.get(definition.translation_key, 0.0)
            label = translations.price_sensor_labels.get(
                definition.translation_key, definition.translation_key
            )
            impact = (
                translations.price_income_label
                if definition.is_credit
                else translations.price_expense_label
            )
            if definition.is_credit:
                income_total += value
            else:
                expenses_total += value
            price_rows.append((label, _format_number(value), impact))

        if price_rows:
            price_widths = builder.compute_column_widths((0.5, 0.28, 0.22))
            builder.add_table(
                TableConfig(
                    title=translations.price_table_title,
                    headers=translations.price_table_headers,
                    rows=price_rows,
                    column_widths=price_widths,
                )
            )

            balance = income_total - expenses_total
            builder.add_paragraph(
                translations.price_balance_sentence.format(
                    expenses=_format_number(expenses_total),
                    income=_format_number(income_total),
                    balance=_format_number(balance),
                ),
                bold=True,
            )


    totals_map = co2_totals or {}
    co2_rows: list[tuple[str, str, str]] = []
    emissions_total = 0.0
    savings_total = 0.0


    if co2_definitions:
        builder.add_section_title(translations.co2_section_title)
        builder.add_paragraph(translations.co2_section_intro)

        co2_rows: list[tuple[str, str, str]] = []
        emissions_total = 0.0
        savings_total = 0.0

        for definition in co2_definitions:
            value = totals_map.get(definition.translation_key, 0.0)
            label = translations.co2_sensor_labels.get(
                definition.translation_key, definition.translation_key
            )
            if definition.is_saving:
                impact = translations.co2_savings_label
                savings_total += value
            else:
                impact = translations.co2_emission_label
                emissions_total += value
            co2_rows.append((label, _format_number(value), impact))

        if co2_rows:
            co2_widths = builder.compute_column_widths((0.5, 0.28, 0.22))
            builder.add_table(
                TableConfig(
                    title=translations.co2_table_title,
                    headers=translations.co2_table_headers,
                    rows=co2_rows,
                    column_widths=co2_widths,
                )
            )

            balance = emissions_total - savings_total
            builder.add_paragraph(
                translations.co2_balance_sentence.format(
                    emissions=f"{_format_number(emissions_total)} kgCO₂e",
                    savings=f"{_format_number(savings_total)} kgCO₂e",
                    balance=f"{_format_number(balance)} kgCO₂e",
                ),
                bold=True,
            )



    if conclusion_summary:
        builder.add_section_title(translations.conclusion_title)

        overview_text = _render_conclusion_overview(translations, conclusion_summary)
        builder.add_paragraph(overview_text)

        formatted_values = conclusion_summary.formatted
        table_rows: list[tuple[str, str]] = [
            (translations.conclusion_row_direct_label, formatted_values["direct"]),
        ]
        emphasize_rows: list[int] = [0]

        if conclusion_summary.has_battery:
            indirect_value = formatted_values.get("indirect")
            if indirect_value:
                table_rows.append(
                    (
                        translations.conclusion_row_indirect_label,
                        indirect_value,
                    )
                )
                emphasize_rows.append(len(table_rows) - 1)

        table_rows.extend(
            [
                (
                    translations.conclusion_row_production_label,
                    formatted_values["production"],
                ),
                (
                    translations.conclusion_row_import_label,
                    formatted_values["imported"],
                ),
                (
                    translations.conclusion_row_export_label,
                    formatted_values["exported"],
                ),
                (
                    translations.conclusion_row_consumption_label,
                    formatted_values["consumption"],
                ),
                (
                    translations.conclusion_row_total_consumption_label,
                    formatted_values["total_consumption"],
                ),
                (
                    translations.conclusion_row_untracked_consumption_label,
                    formatted_values["untracked_consumption"],
                ),
            ]
        )

        table_widths = builder.compute_column_widths((0.62, 0.38))
        builder.add_table(
            TableConfig(
                title=translations.conclusion_table_title,
                headers=translations.conclusion_table_headers,
                rows=table_rows,
                column_widths=table_widths,
                emphasize_rows=emphasize_rows,
            )
        )

    builder.add_paragraph(translations.conclusion_hint)

    advice_content = advice_text.strip() if advice_text else ""
    if not advice_content:
        advice_content = FALLBACK_MESSAGE

    builder.add_section_title(translations.advice_section_title)
    builder.add_paragraph(advice_content)

    builder.add_footer(translations.footer_path.format(path=file_path))

    builder.output(str(file_path))

    return str(file_path)


def _prepare_summary_rows(
    metrics: Iterable[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, float, str]]]:
    """Préparer les lignes du tableau de synthèse et la série pour les graphiques."""

    summary: dict[tuple[str, str], float] = defaultdict(float)

    for metric in metrics:
        total = totals.get(metric.statistic_id)
        if total is None:
            continue
        unit = _extract_unit(metadata.get(metric.statistic_id))
        key = (metric.category, unit)
        summary[key] += total

    rows: list[tuple[str, str, str]] = []
    series: list[tuple[str, float, str]] = []
    for (category, unit), value in sorted(
        summary.items(), key=lambda item: (-abs(item[1]), item[0])
    ):
        if abs(value) < 1e-6:
            continue
        decorated = _decorate_category(category)
        rows.append((decorated, _format_number(value), unit))
        series.append((decorated, value, unit))

    return rows, series


def _prepare_detail_rows(
    metrics: Iterable[MetricDefinition],
    totals: dict[str, float],
    metadata: dict[str, tuple[int, StatisticMetaData]],
    cost_mapping: Mapping[str, str],
) -> list[tuple[str, str, str, str]]:
    """Préparer les lignes détaillées du rapport."""

    cost_stats = {value for value in cost_mapping.values() if value}
    details: list[tuple[str, str, float, str]] = []
    for metric in metrics:
        if metric.statistic_id in cost_stats:
            continue
        total = totals.get(metric.statistic_id, 0.0)
        meta_entry = metadata.get(metric.statistic_id)
        name = _extract_name(meta_entry, metric.statistic_id)
        unit = _extract_unit(meta_entry)
        details.append((metric.category, name, total, unit))

    details.sort(key=lambda item: (item[0], -abs(item[2]), item[1]))

    rows: list[tuple[str, str, str, str]] = []
    for category, name, value, unit in details:
        rows.append((category, name, _format_number(value), unit))

    return rows

_CONCLUSION_CATEGORY_MAP = {
    "Production solaire": "production",
    "Import réseau": "imported",
    "Export réseau": "exported",
    "Consommation appareils": "consumption",
    "Charge batterie": "charge",
    "Décharge batterie": "discharge",
}


def _prepare_conclusion_summary(
    metrics: Iterable[MetricDefinition],
    totals: Mapping[str, float],
    metadata: Mapping[str, tuple[int, StatisticMetaData]],
) -> ConclusionSummary | None:
    """Assembler les données nécessaires pour la conclusion."""

    category_totals: dict[str, float] = {
        value: 0.0 for value in _CONCLUSION_CATEGORY_MAP.values()
    }
    energy_unit: str | None = None
    has_values = False

    for metric in metrics:
        key = _CONCLUSION_CATEGORY_MAP.get(metric.category)
        if key is None:
            continue

        total = totals.get(metric.statistic_id)
        if total is None:
            continue

        has_values = True
        category_totals[key] += total

        if energy_unit:
            continue
        unit_candidate = _extract_unit(metadata.get(metric.statistic_id)).strip()
        if unit_candidate:
            energy_unit = unit_candidate

    if not has_values:
        return None

    production = category_totals["production"]
    imported = category_totals["imported"]
    exported = category_totals["exported"]
    consumption = category_totals["consumption"]
    charge = category_totals["charge"]
    discharge = category_totals["discharge"]

    direct_self_consumption = max(
        production - max(exported, 0.0) - max(charge, 0.0),
        0.0,
    )

    battery_detected = any(
        metric.category in ("Charge batterie", "Décharge batterie") for metric in metrics
    )

    indirect_self_consumption: float | None = None
    if battery_detected:
        indirect_self_consumption = max(min(discharge, charge), 0.0)

    total_estimated_consumption = (
        production + imported + discharge - exported - charge
    )
    untracked_consumption = max(
        total_estimated_consumption - consumption, 0.0
    )

    formatted_values: dict[str, str] = {
        "production": _format_with_unit(production, energy_unit),
        "direct": _format_with_unit(direct_self_consumption, energy_unit),
        "imported": _format_with_unit(imported, energy_unit),
        "exported": _format_with_unit(exported, energy_unit),
        "consumption": _format_with_unit(consumption, energy_unit),
        "total_consumption": _format_with_unit(
            total_estimated_consumption, energy_unit
        ),
        "untracked_consumption": _format_with_unit(
            untracked_consumption, energy_unit
        ),
    }

    if indirect_self_consumption is not None:
        formatted_values["indirect"] = _format_with_unit(
            indirect_self_consumption, energy_unit
        )

    return ConclusionSummary(
        production=production,
        imported=imported,
        exported=exported,
        consumption=consumption,
        charge=charge,
        discharge=discharge,
        direct=direct_self_consumption,
        indirect=indirect_self_consumption,
        total_estimated_consumption=total_estimated_consumption,
        untracked_consumption=untracked_consumption,
        has_battery=battery_detected,
        energy_unit=energy_unit,
        formatted=formatted_values,
    )


def _render_conclusion_overview(
    translations: ReportTranslations, summary: ConclusionSummary
) -> str:
    """Construire le paragraphe de conclusion affiché et envoyé à l’IA."""

    formatted = summary.formatted

    if summary.has_battery and summary.indirect is not None:
        return translations.conclusion_overview_with_battery.format(
            production=formatted["production"],
            direct=formatted["direct"],
            indirect=formatted.get("indirect", ""),
            imported=formatted["imported"],
            exported=formatted["exported"],
            consumption=formatted["consumption"],
            total_consumption=formatted["total_consumption"],
            untracked_consumption=formatted["untracked_consumption"],
        )

    return translations.conclusion_overview_without_battery.format(
        production=formatted["production"],
        direct=formatted["direct"],
        imported=formatted["imported"],
        exported=formatted["exported"],
        consumption=formatted["consumption"],
        total_consumption=formatted["total_consumption"],
        untracked_consumption=formatted["untracked_consumption"],
    )


def _compose_conclusion_prompt(
    translations: ReportTranslations, summary: ConclusionSummary | None
) -> str:
    """Assembler un texte descriptif passé à l’IA pour générer un conseil."""

    if summary is None:
        return translations.conclusion_hint

    overview = _render_conclusion_overview(translations, summary)
    formatted = summary.formatted

    rows: list[tuple[str, str]] = [
        (translations.conclusion_row_direct_label, formatted["direct"]),
    ]

    if summary.has_battery and summary.indirect is not None:
        rows.append(
            (translations.conclusion_row_indirect_label, formatted["indirect"])
        )

    rows.extend(
        [
            (
                translations.conclusion_row_production_label,
                formatted["production"],
            ),
            (
                translations.conclusion_row_import_label,
                formatted["imported"],
            ),
            (
                translations.conclusion_row_export_label,
                formatted["exported"],
            ),
            (
                translations.conclusion_row_consumption_label,
                formatted["consumption"],
            ),
            (
                translations.conclusion_row_total_consumption_label,
                formatted["total_consumption"],
            ),
            (
                translations.conclusion_row_untracked_consumption_label,
                formatted["untracked_consumption"],
            ),
        ]
    )

    table_lines = "\n".join(f"{label} : {value}" for label, value in rows)

    return (
        f"{overview}\n\n{translations.conclusion_table_title} :\n{table_lines}"
    )


def _extract_unit(metadata: tuple[int, StatisticMetaData] | None) -> str:
    """Récupérer l'unité depuis les métadonnées."""

    if metadata and metadata[1].get("unit_of_measurement"):
        return str(metadata[1]["unit_of_measurement"])
    return ""


def _extract_name(
    metadata: tuple[int, StatisticMetaData] | None, fallback: str
) -> str:
    """Récupérer le nom lisible d'une statistique."""

    if metadata:
        # Essayer le friendly_name stocké dans les métadonnées
        name = metadata[1].get("name")
        if name is not None:
            name_str = str(name).strip()
            if name_str:
                return name_str

        # Essayer une description éventuelle
        desc = metadata[1].get("statistic_id")
        if desc and str(desc).strip():
            return str(desc)

    return fallback


def _safe_float(value: Any) -> float | None:
    """Convertir une valeur en flottant si possible."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    """Formater une valeur numérique de manière lisible."""

    if abs(value) < 0.0005:
        value = 0.0

    if abs(value) >= 1000:
        formatted = f"{value:,.0f}"
    elif abs(value) >= 10:
        formatted = f"{value:,.1f}"
    else:
        formatted = f"{value:,.3f}"

    return formatted.replace(",", " ")


def _format_with_unit(value: float, unit: str | None) -> str:
    """Associer un formatage numérique avec une unité si disponible."""

    formatted = _format_number(value)
    return f"{formatted} {unit}".strip() if unit else formatted


__all__ = ["async_setup", "async_setup_entry", "async_unload_entry"]

