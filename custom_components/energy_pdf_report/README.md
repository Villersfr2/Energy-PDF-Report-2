# Energy PDF Report

Generate beautifully formatted PDF summaries of your Home Assistant Energy Dashboard data. The Energy PDF Report custom integration aggregates production, consumption, battery flow, prices, and CO₂ metrics into a localized report that you can archive or share with the people in your home.

## Key features

- **One-click PDF generation** – call a single Home Assistant service to produce day, week, or month reports with accurate per-period statistics.
- **Energy comparison insights** – optionally compare two periods; the integration highlights deltas for production, imports/exports, self-consumption, and untracked usage directly in the conclusion text and comparison tables.
- **Localized output** – reports are available in French, English, and Dutch; all headings, tables, and the AI-generated narrative follow the selected language.
- **Flexible data sources** – track electricity, gas/mazout, water, price, and CO₂ sensors with per-integration defaults that you can override from the options flow.
- **AI-powered recommendations** – provide your own OpenAI API key to append personalized energy-saving advice tailored to the generated report (including comparison insights when enabled).
- **Collision-free filenames** – every generated PDF automatically receives a four-character random suffix, preserving subdirectories while avoiding accidental overwrites.

## Requirements

- Home Assistant with the Energy Dashboard configured and recording statistics for the entities you want to include.
- Recorder enabled so historical statistics can be fetched for the requested period(s).
- (Optional) An OpenAI API key if you want to enable the advisor section of the report.

## Installation via HACS

1. Confirm that [HACS](https://hacs.xyz/) is installed and configured in your Home Assistant instance.
2. Navigate to **HACS → Integrations**, open the overflow menu (⋮), and choose **Custom repositories**.
3. Enter the repository URL (for example `https://github.com/OWNER/Energy-PDF-Report-2`) and set the category to **Integration**, then click **Add**.
4. Close the dialog, search for **Energy PDF Report** in **HACS → Integrations**, and install it.
5. Restart Home Assistant if prompted, then add the integration from **Settings → Devices & Services → Add Integration**.

### Manual installation

Copy the `custom_components/energy_pdf_report` folder into your Home Assistant `config/custom_components` directory, restart Home Assistant, and add the integration from **Settings → Devices & Services**. Manual installations will not receive automatic updates.

## Configuration options

After adding the integration, open **Settings → Devices & Services → Energy PDF Report → Configure** to adjust the following options:

| Option | Description | Default |
| ------ | ----------- | ------- |
| `output_dir` | Relative path inside your Home Assistant configuration directory where PDFs are stored. | `www/energy_reports` |
| `filename_pattern` | Pattern used to build the base filename before the random suffix is appended. The template supports `{language}`, `{start}`, and `{end}` placeholders. | `energy_report_{language}_{start}_{end}.pdf` |
| `default_report_type` | Default period suggested when you open the service dialog. Supported values: `day`, `week`, `month`. | `week` |
| `language` | Default language used when none is provided in the service call. | `fr` |
| `co2_sensor_*` | Entity IDs for electricity, gas/mazout, water, and savings CO₂ sensors. | Pre-filled with recommended sensors; savings is optional. |
| `price_sensor_*` | Entity IDs for electricity import/export, gas/mazout, and water price sensors. | Pre-filled with recommended sensors. |
| `co2_enabled` | Include CO₂ rows in the PDF when enabled. | `false` |
| `price_enabled` | Include price and revenue rows in the PDF when enabled. | `false` |
| `dashboard` | Energy Dashboard configuration ID to pull statistics from (leave blank to use the default dashboard). | *(empty)* |
| `openai_api_key` | API key used to request AI-generated advice. Leave blank to disable the advisor section. | *(empty)* |

## Generating a report

Use the `energy_pdf_report.generate` service from **Developer Tools → Services**, an automation, or the Home Assistant API. Available service fields are:

| Field | Type | Description |
| ----- | ---- | ----------- |
| `start_date` | Date | First day included in the report. If omitted, the integration infers the range from `period`. |
| `end_date` | Date | Last day included in the report. When omitted, the integration uses the current day based on the selected `period`. |
| `period` | String | Aggregation period (`day`, `week`, or `month`). Defaults to the integration option or `day` when unset. |
| `filename` | String | Optional custom filename (without directory). A random suffix is always appended before the extension. |
| `output_dir` | String | Override the configured output directory for this run. |
| `language` | String | Override the default report language (`fr`, `en`, or `nl`). |
| `dashboard` | String | Override the dashboard ID to pull statistics from. |
| `co2_enabled` | Boolean | Temporarily include or hide the CO₂ section regardless of the saved option. |
| `price_enabled` | Boolean | Temporarily include or hide the price section regardless of the saved option. |
| `compare` | Boolean | Enable comparison with a secondary period. Requires `compare_start_date` and `compare_end_date`. |
| `compare_start_date` | Date | First day of the comparison range when `compare` is true. |
| `compare_end_date` | Date | Last day of the comparison range when `compare` is true. |

### How the `period` field is used

- **Default range selection** – When `start_date` or `end_date` is omitted, the integration expands the selected `period` into an inclusive date window before fetching energy, price, and CO₂ statistics.
- **Recorder granularity** – The same `period` drives the statistic bucket (`hour` or `day`) requested from the recorder so that the totals match the Energy Dashboard view for that range.
- **File naming** – The resolved `period` value is injected into the filename pattern, allowing you to build names such as `energy_report_week_2024-10-04_2024-10-10.pdf` automatically.

Example service call:

```yaml
service: energy_pdf_report.generate
data:
  period: week
  start_date: "2024-01-01"
  end_date: "2024-01-07"
  compare: true
  compare_start_date: "2023-12-25"
  compare_end_date: "2023-12-31"
  language: en
```

The PDF is saved inside the configured `output_dir`. If you keep the default path, the file will be available under `/config/www/energy_reports` and can be downloaded from the Home Assistant file browser or served through the `/local/` URL (for example `/local/energy_reports/energy_report_en_2024-01-01_2024-01-07_ABCD.pdf`).

## Automating report generation

Schedule recurring reports using standard Home Assistant automations. The example below generates a monthly English report on the first day of each month and sends a link through a notification:

```yaml
alias: Monthly energy PDF
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
action:
  - service: energy_pdf_report.generate
    data:
      period: month
      language: en
  - delay: "00:01:00"  # wait for the PDF to be written
  - service: notify.mobile_app_phone
    data:
      title: "Monthly energy report"
      message: "Your latest energy PDF is available in /local/energy_reports/."
mode: single
```

## Troubleshooting

- Ensure the recorder includes statistics for every entity referenced by the integration; missing statistics will prevent the related rows from appearing.
- When tracking very small CO₂ or price counters (for example water emissions around `0.039` kgCO₂e per day), the integration accumulates their daily statistics with decimal arithmetic and the PDF prints those values without rounding so they can be re-used in downstream calculations.
- If the report generation service fails, check **Settings → System → Logs** for detailed error messages.
- When the AI advisor is enabled, verify that your OpenAI API key is valid and that outbound HTTPS requests are permitted from your Home Assistant host.

For questions, feature requests, or bug reports, please open an issue on the repository.
