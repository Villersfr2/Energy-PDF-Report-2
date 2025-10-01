# EcoPilot PDF Report

Generate PDF energy reports directly from your Home Assistant instance using the EcoPilot PDF Report custom integration.

## Installation via HACS

1. Confirm that [HACS](https://hacs.xyz/) is installed and configured in your Home Assistant instance.
2. Navigate to **HACS → Integrations** and select the overflow menu (⋮) in the top-right corner.
3. Choose **Custom repositories**, enter the GitHub URL for this repository (for example, `https://github.com/OWNER/ecopilot-pdf-report`), and set the category to **Integration**.
4. Click **Add** to register the repository and close the dialog.
5. Back in **HACS → Integrations**, search for **EcoPilot PDF Report** and select it.
6. Click **Download** and follow the prompts to install the integration, then restart Home Assistant if prompted.
7. After Home Assistant reloads, open **Settings → Integrations**, click **Add Integration**, search for **EcoPilot PDF Report**, and complete the setup so it appears in your integrations list.

## Configuration

The integration exposes configurable options that can be adjusted from the integration entry's **Options** dialog in Home Assistant:

- `output_dir`: Directory where generated PDF reports are stored.
- `filename_pattern`: Template used to name generated PDF files.
- `default_report_type`: Report type selected by default when generating PDFs.
- `language`: Preferred language for generated reports.
- `co2_electricity_sensor`: Entity ID used to track electricity-related CO₂ emissions in the report.
- `co2_gas_sensor`: Entity ID used to track gas-related CO₂ emissions in the report.
- `co2_water_sensor`: Entity ID used to track water-related CO₂ emissions in the report.
- `co2_savings_sensor`: Entity ID used to track CO₂ savings. Leave blank if you do not want the savings row in the PDF.

You can revisit the integration options at any time via **Settings → Devices & Services → EcoPilot PDF Report → Configure** to update these values.

## Triggering the service

The integration provides the `energy_pdf_report.generate_report` service. You can trigger it from **Developer Tools → Services** or via YAML automation as shown below:

```yaml
service: energy_pdf_report.generate_report
data:
  report_type: daily
  start_date: "2024-01-01"
  end_date: "2024-01-07"
  output_dir: "/config/www/reports"
  filename: "weekly_energy_report.pdf"
```

Adjust the parameters to suit your environment or omit optional fields to rely on the configured defaults.
