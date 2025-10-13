"""Constantes de l'intégration energy_pdf_report."""

from __future__ import annotations

DOMAIN = "energy_pdf_report"
SERVICE_GENERATE_REPORT = "generate"
DEFAULT_PERIOD = "day"
VALID_PERIODS: tuple[str, ...] = ("day", "week", "month", "custom")

DEFAULT_REPORT_TYPE = "week"

VALID_REPORT_TYPES = VALID_PERIODS
DEFAULT_OUTPUT_DIR = "www/energy_reports"
DEFAULT_FILENAME_PATTERN = "energy_report_{language}_{start}_{end}.pdf"
DEFAULT_LANGUAGE = "fr"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("fr", "nl", "en")

CONF_START_DATE = "start_date"
CONF_END_DATE = "end_date"
CONF_PERIOD = "period"
CONF_OUTPUT_DIR = "output_dir"
CONF_DASHBOARD = "dashboard"
CONF_FILENAME_PATTERN = "filename_pattern"
CONF_DEFAULT_REPORT_TYPE = "default_report_type"
CONF_COMPARE = "compare"
CONF_COMPARE_START_DATE = "compare_start_date"
CONF_COMPARE_END_DATE = "compare_end_date"

CONF_LANGUAGE = "language"
CONF_CO2 = "co2_enabled"
CONF_PRICE = "price_enabled"

CONF_CO2_ELECTRICITY = "co2_sensor_electricity"
CONF_CO2_GAS = "co2_sensor_gas"
CONF_CO2_WATER = "co2_sensor_water"
CONF_CO2_SAVINGS = "co2_sensor_savings"

CONF_PRICE_ELECTRICITY_IMPORT = "price_sensor_electricity_import"
CONF_PRICE_ELECTRICITY_EXPORT = "price_sensor_electricity_export"
CONF_PRICE_GAS = "price_sensor_gas"
CONF_PRICE_WATER = "price_sensor_water"

CONF_OPENAI_API_KEY = "openai_api_key"

DEFAULT_CO2_ELECTRICITY_SENSOR = "sensor.co2_emissions_today"
DEFAULT_CO2_GAS_SENSOR = "sensor.co2_gaz_jour"
DEFAULT_CO2_WATER_SENSOR = "sensor.co2_eau_jour"
DEFAULT_CO2_SAVINGS_SENSOR = "sensor.co2_savings_today"

DEFAULT_PRICE_ELECTRICITY_IMPORT_SENSOR = "sensor.cout_prelevement_electricite"
DEFAULT_PRICE_ELECTRICITY_EXPORT_SENSOR = "sensor.revenus_injection_electricite"
DEFAULT_PRICE_GAS_SENSOR = "sensor.energy_gas_cost"
DEFAULT_PRICE_WATER_SENSOR = "sensor.energy_water_cost"

DEFAULT_CO2 = False
DEFAULT_PRICE = False


PDF_TITLE = "Rapport énergie"
