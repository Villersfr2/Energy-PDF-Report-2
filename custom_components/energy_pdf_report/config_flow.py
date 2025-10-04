"""Flux de configuration pour l'intégration Energy PDF Report."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
try:
    from homeassistant.data_entry_flow import FlowResult
except ImportError:  # pragma: no cover - compat with older versions
    FlowResult = dict[str, Any]

from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CO2,
    CONF_CO2_ELECTRICITY,
    CONF_CO2_GAS,
    CONF_CO2_SAVINGS,
    CONF_CO2_WATER,
    CONF_DEFAULT_REPORT_TYPE,
    CONF_FILENAME_PATTERN,
    CONF_LANGUAGE,
    CONF_OUTPUT_DIR,
    CONF_PRICE,
    CONF_PRICE_ELECTRICITY_EXPORT,
    CONF_PRICE_ELECTRICITY_IMPORT,
    CONF_PRICE_GAS,
    CONF_PRICE_WATER,
    CONF_OPENAI_API_KEY,
    DEFAULT_CO2,
    DEFAULT_CO2_ELECTRICITY_SENSOR,
    DEFAULT_CO2_GAS_SENSOR,
    DEFAULT_CO2_SAVINGS_SENSOR,
    DEFAULT_CO2_WATER_SENSOR,
    DEFAULT_FILENAME_PATTERN,
    DEFAULT_LANGUAGE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRICE,
    DEFAULT_PRICE_ELECTRICITY_EXPORT_SENSOR,
    DEFAULT_PRICE_ELECTRICITY_IMPORT_SENSOR,
    DEFAULT_PRICE_GAS_SENSOR,
    DEFAULT_PRICE_WATER_SENSOR,
    DEFAULT_REPORT_TYPE,
    DOMAIN,
    SUPPORTED_LANGUAGES,
    VALID_REPORT_TYPES,
)

# Définitions des capteurs CO₂ avec leurs valeurs par défaut
CO2_SENSOR_DEFAULTS: tuple[tuple[str, str], ...] = (
    (CONF_CO2_ELECTRICITY, DEFAULT_CO2_ELECTRICITY_SENSOR),
    (CONF_CO2_GAS, DEFAULT_CO2_GAS_SENSOR),
    (CONF_CO2_WATER, DEFAULT_CO2_WATER_SENSOR),
    (CONF_CO2_SAVINGS, DEFAULT_CO2_SAVINGS_SENSOR),
)

# Définitions des capteurs de prix avec leurs valeurs par défaut
PRICE_SENSOR_DEFAULTS: tuple[tuple[str, str], ...] = (
    (CONF_PRICE_ELECTRICITY_IMPORT, DEFAULT_PRICE_ELECTRICITY_IMPORT_SENSOR),
    (CONF_PRICE_ELECTRICITY_EXPORT, DEFAULT_PRICE_ELECTRICITY_EXPORT_SENSOR),
    (CONF_PRICE_GAS, DEFAULT_PRICE_GAS_SENSOR),
    (CONF_PRICE_WATER, DEFAULT_PRICE_WATER_SENSOR),
)

# Valeurs par défaut globales
BASE_DEFAULTS: dict[str, Any] = {
    CONF_OUTPUT_DIR: DEFAULT_OUTPUT_DIR,
    CONF_FILENAME_PATTERN: DEFAULT_FILENAME_PATTERN,
    CONF_DEFAULT_REPORT_TYPE: DEFAULT_REPORT_TYPE,
    CONF_LANGUAGE: DEFAULT_LANGUAGE,
    CONF_CO2: DEFAULT_CO2,
    CONF_PRICE: DEFAULT_PRICE,
    CONF_OPENAI_API_KEY: "",
}
for option_key, default in CO2_SENSOR_DEFAULTS:
    BASE_DEFAULTS[option_key] = default
for option_key, default in PRICE_SENSOR_DEFAULTS:
    BASE_DEFAULTS[option_key] = default


def _merge_defaults(existing: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Retourner les valeurs de config fusionnées avec les valeurs par défaut."""
    merged: dict[str, Any] = dict(BASE_DEFAULTS)
    if existing:
        for key, value in existing.items():
            if value is not None:
                merged[key] = value
    # Garde-fou: s'assurer que default_report_type est valide
    if merged.get(CONF_DEFAULT_REPORT_TYPE) not in VALID_REPORT_TYPES:
        merged[CONF_DEFAULT_REPORT_TYPE] = DEFAULT_REPORT_TYPE
    return merged


def _build_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Construire le schéma voluptuous pour le flow."""
    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_OUTPUT_DIR, default=defaults[CONF_OUTPUT_DIR]): cv.string,
        vol.Required(CONF_FILENAME_PATTERN, default=defaults[CONF_FILENAME_PATTERN]): cv.string,
        vol.Required(
            CONF_DEFAULT_REPORT_TYPE,
            default=defaults[CONF_DEFAULT_REPORT_TYPE],
        ): vol.In(VALID_REPORT_TYPES),
        vol.Required(CONF_LANGUAGE, default=defaults[CONF_LANGUAGE]): vol.In(
            SUPPORTED_LANGUAGES
        ),
        vol.Required(CONF_CO2, default=defaults[CONF_CO2]): cv.boolean,
        vol.Required(CONF_PRICE, default=defaults[CONF_PRICE]): cv.boolean,
    }

    # Ajout des capteurs CO₂ (optionnels pour éviter un crash si vide)
    for option_key, default in CO2_SENSOR_DEFAULTS:
        schema_dict[
            vol.Optional(option_key, default=defaults[option_key])
        ] = cv.string

    # Ajout des capteurs de prix (optionnels également)
    for option_key, default in PRICE_SENSOR_DEFAULTS:
        schema_dict[
            vol.Optional(option_key, default=defaults[option_key])
        ] = cv.string

    schema_dict[
        vol.Optional(
            CONF_OPENAI_API_KEY, default=defaults[CONF_OPENAI_API_KEY]
        )
    ] = cv.string

    return vol.Schema(schema_dict)


class _EnergyPDFReportConfigFlow(config_entries.ConfigFlow):
    """Base config flow for Energy PDF Report."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialiser le flow de config."""
        self._reconfigure_entry: config_entries.ConfigEntry | None = None
        self._cached_existing_values: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape initiale."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            self._cached_existing_values = None

            return self.async_create_entry(
                title="Energy PDF Report",
                data=user_input,
            )

        if self._reconfigure_entry is None:
            existing_entries = self._async_current_entries()
            if existing_entries:
                entry = existing_entries[0]
                self._reconfigure_entry = entry
                self._cached_existing_values = {
                    **dict(entry.data),
                    **dict(entry.options),
                }
                self.context["title_placeholders"] = {
                    "title": entry.title or "Energy PDF Report",
                }
                return await self.async_step_reinstall_confirm()

        defaults = _merge_defaults(self._cached_existing_values)
        self._cached_existing_values = None

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(defaults),
            errors={},
        )

    async def async_step_reinstall_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirmer avant de remplacer une entrée existante."""
        entry = self._reconfigure_entry
        if entry is None:
            return await self.async_step_user(user_input)

        if user_input is None:
            return self.async_show_form(
                step_id="reinstall_confirm",
                data_schema=vol.Schema({}),
            )

        if entry.unique_id is None:
            self.hass.config_entries.async_update_entry(entry, unique_id=DOMAIN)

        try:
            removal_result = await self.hass.config_entries.async_remove(entry.entry_id)
        except HomeAssistantError:
            removal_result = False

        if removal_result is False:
            self._cached_existing_values = None
            self._reconfigure_entry = None
            return self.async_abort(reason="remove_failed")

        self._reconfigure_entry = None
        return await self.async_step_user()

class EnergyPDFReportConfigFlow(_EnergyPDFReportConfigFlow):
    """Config flow for Energy PDF Report."""

    domain = DOMAIN


class ConfigFlow(EnergyPDFReportConfigFlow):
    """Expose the flow under the legacy ``ConfigFlow`` name."""


class EnergyPDFReportOptionsFlowHandler(config_entries.OptionsFlow):
    """Gérer les options pour Energy PDF Report."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialiser le flow d’options."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Gérer les options Energy PDF Report."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = _merge_defaults(
            {
                **self.config_entry.data,
                **self.config_entry.options,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
        )


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    """Retourner le gestionnaire d’options."""
    return EnergyPDFReportOptionsFlowHandler(config_entry)
