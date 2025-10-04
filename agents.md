Project: EcoPilot PDF Reporting Tool

Type: Home Assistant Custom Component
Purpose: Generate detailed PDF energy reports using Home Assistant Energy Dashboard data (statistics + history).
Languages: fr / en / nl
Core files:

custom_components/ecopilot_pdf_report/__init__.py → data collection, service, pricing & CO₂ logic

pdf.py → PDF generation

config_flow.py → UI configuration (options + defaults)

const.py → constants (sensor defaults, keys)
ai_helper.py  → generate aI advice for the Ecopilot conseiller in the pdf rapportUI configuration (options + defaults)
Key Functions to Understand

_async_handle_generate: orchestrates the report generation (data fetching + PDF creation)

CO₂ & Price values must be collected as “last state per day” for each day in the period, then summed.

For 1-day reports → take the last state of that day only (don’t include the next day).

Energy values come from Home Assistant’s Energy Dashboard (already normalized in kWh).
Do not convert Wh↔kWh inside the component anymore.

Sensor IDs for pricing and CO₂ are configurable by the user or fallback to const.py.

Tasks Codex Might Need to Do

Modify __init__.py to use Recorder / History to get last state per day for price & CO₂ sensors.

Fix logic where 1-day reports incorrectly include the next day's value.

Replace any normalize_to_kwh usage for device consumption with dashboard-based values.

Ensure the code uses the configured sensor IDs, not hardcoded ones.

Keep the existing PDF structure intact.

Technical Constraints

Use Home Assistant's modern history API (e.g. instance.async_add_executor_job) for data retrieval.

No blocking I/O in the event loop.

Keep the language of the AI advice section the same as the report language.

Keep compatibility with the current config_flow and service schema.

Example Service Call
service: ecopilot_pdf_report.generate
data:
  start_date: "2025-10-01"
  end_date: "2025-10-03"
  period: "day"
  language: "fr"
