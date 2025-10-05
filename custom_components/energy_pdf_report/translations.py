"""Traductions statiques pour la génération des rapports PDF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .const import DEFAULT_LANGUAGE


@dataclass(frozen=True)
class ReportTranslations:
    """Regroupe les chaînes localisées utilisées dans le rapport."""

    language: str
    pdf_title: str
    cover_subtitle: str
    cover_period: str
    cover_dashboard: str
    cover_bucket: str
    cover_stats: str
    cover_generated: str
    summary_title: str
    summary_intro: str
    summary_table_title: str
    summary_headers: tuple[str, str, str]
    summary_row_total_consumption_label: str
    summary_row_untracked_consumption_label: str
    summary_note_totals: str
    summary_note_negative: str
    detail_title: str
    detail_intro: str
    detail_table_title: str
    detail_headers: tuple[str, str, str, str]
    chart_intro: str
    chart_title: str
    chart_units: str
    price_section_title: str
    price_section_intro: str
    price_table_title: str
    price_table_headers: tuple[str, str, str]
    price_expense_label: str
    price_income_label: str
    price_balance_sentence: str
    price_sensor_labels: Mapping[str, str]
    co2_section_title: str
    co2_section_intro: str
    co2_table_title: str
    co2_table_headers: tuple[str, str, str]
    co2_emission_label: str
    co2_savings_label: str
    co2_balance_sentence: str
    co2_sensor_labels: Mapping[str, str]
    comparison_section_title: str
    comparison_table_title: str
    comparison_header_category: str
    comparison_header_difference: str
    comparison_header_variation: str
    comparison_consumption_label: str
    comparison_battery_charge_label: str
    comparison_battery_discharge_label: str
    comparison_total_estimated_consumption_label: str
    comparison_untracked_consumption_label: str
    comparison_device_consumption_label: str
    comparison_production_label: str
    comparison_import_label: str
    comparison_export_label: str
    comparison_self_consumption_label: str
    comparison_expense_label: str
    comparison_income_label: str
    comparison_co2_label: str
    comparison_water_consumption_label: str
    comparison_gas_consumption_label: str
    conclusion_title: str
    conclusion_overview_without_battery: str
    conclusion_overview_with_battery: str
    conclusion_table_title: str
    conclusion_table_headers: tuple[str, str]
    conclusion_row_direct_label: str
    conclusion_row_indirect_label: str
    conclusion_row_production_label: str
    conclusion_row_import_label: str
    conclusion_row_export_label: str
    conclusion_row_consumption_label: str
    conclusion_row_total_consumption_label: str
    conclusion_row_untracked_consumption_label: str
    conclusion_hint: str
    conclusion_comparison_insight: str
    advice_section_title: str
    footer_path: str
    footer_page: str
    footer_generated: str
    table_empty: str
    bucket_labels: Mapping[str, str]
    period_labels: Mapping[str, str]
    notification_title: str
    notification_line_period: str
    notification_line_dashboard: str
    notification_line_download: str
    notification_line_file: str


_TRANSLATIONS: dict[str, ReportTranslations] = {
    "fr": ReportTranslations(
        language="fr",
        pdf_title="Rapport énergie",
        cover_subtitle="Rapport énergie du {start} au {end}",
        cover_period="Période : {period}",
        cover_dashboard="Tableau d'énergie : {dashboard}",
        cover_bucket="Granularité des statistiques : {bucket}",
        cover_stats="Statistiques incluses : {count}",
        cover_generated="Rapport généré le : {timestamp}",
        summary_title="Résumé global",
        summary_intro="Cette section présente les totaux consolidés sur la période analysée.",
        summary_table_title="Synthèse par catégorie",
        summary_headers=("Catégorie", "Total", "Unité"),
        summary_row_total_consumption_label="Consommation totale estimée",
        summary_row_untracked_consumption_label="Consommation non suivie",
        summary_note_totals="Les totaux correspondent à la variation mesurée dans le tableau de bord énergie sur la période sélectionnée.",
        summary_note_negative="Les valeurs négatives indiquent un flux exporté ou une compensation.",
        detail_title="Analyse par catégorie / source",
        detail_intro="Chaque statistique suivie est listée avec son énergie afin de faciliter l'analyse fine par origine ou type de consommation.",
        detail_table_title="Détail des statistiques",
        detail_headers=("Catégorie", "Statistique", "Total énergie", "Unité"),
        chart_intro="La visualisation suivante met en avant la répartition des flux pour chaque catégorie suivie et matérialise l'équilibre production / consommation.",
        chart_title="Répartition par catégorie",
        chart_units="Unités : {unit}",
        price_section_title="Finances énergie",
        price_section_intro="Cette section synthétise les dépenses et revenus suivis par vos capteurs financiers.",
        price_table_title="Dépenses et compensations",
        price_table_headers=("Source", "Total", "Type"),
        price_expense_label="Dépense",
        price_income_label="Revenu",
        price_balance_sentence="Dépenses totales : {expenses} • Revenus : {income} • Solde net : {balance}.",
        price_sensor_labels={
            "price_electricity_import": "Coût électricité (import)",
            "price_electricity_export": "Compensation export électricité",
            "price_gas": "Coût gaz",
            "price_water": "Coût eau",
        },
        co2_section_title="CO₂",
        co2_section_intro="Cette section met en lumière les émissions et économies de CO₂ enregistrées par les différents postes.",
        co2_table_title="Émissions et économies de CO₂",
        co2_table_headers=("Source", "Total (kgCO₂e)", "Impact"),
        co2_emission_label="Émission",
        co2_savings_label="Économie",
        co2_balance_sentence="Émissions totales : {emissions} • Économies : {savings} • Bilan net : {balance}.",
        co2_sensor_labels={

            "co2_electricity": "Électricité (scope 2)",
            "co2_gas": "Gaz",
            "co2_water": "Eau",
            "co2_savings": "Économies solaire (autoconsommation)",

        },
        comparison_section_title="Comparaison de périodes",
        comparison_table_title="Comparaison synthétique",
        comparison_header_category="Catégorie",
        comparison_header_difference="Différence",
        comparison_header_variation="Variation",
        comparison_consumption_label="Consommation",
        comparison_battery_charge_label="Charge batterie",
        comparison_battery_discharge_label="Décharge batterie",
        comparison_total_estimated_consumption_label="Consommation totale estimée",
        comparison_untracked_consumption_label="Consommation non suivie",
        comparison_device_consumption_label="Consommation appareils",
        comparison_production_label="Production",
        comparison_import_label="Import réseau",
        comparison_export_label="Export réseau",
        comparison_self_consumption_label="Autoconsommation",
        comparison_expense_label="Dépenses",
        comparison_income_label="Revenus",
        comparison_co2_label="CO₂",
        comparison_water_consumption_label="Consommation eau",

        comparison_gas_consumption_label="Consommation gaz / Mazout",

        conclusion_title="Conclusion",
        conclusion_overview_without_battery="Sur la période, la production solaire atteint {production} dont {direct} autoconsommés directement. Les importations réseau totalisent {imported} tandis que {exported} ont été réinjectés, pour une consommation des appareils de {consumption}. La consommation totale estimée atteint {total_consumption} dont {untracked_consumption} non suivie.",
        conclusion_overview_with_battery="Sur la période, la production solaire atteint {production} : {direct} ont été autoconsommés directement et {indirect} via la batterie. Les importations réseau totalisent {imported} tandis que {exported} ont été réinjectés, pour une consommation des appareils de {consumption}. La consommation totale estimée atteint {total_consumption} dont {untracked_consumption} non suivie.",
        conclusion_table_title="Synthèse des flux énergétiques",
        conclusion_table_headers=("Flux", "Total"),
        conclusion_row_direct_label="Autoconsommation directe",
        conclusion_row_indirect_label="Autoconsommation indirecte",
        conclusion_row_production_label="Production solaire",
        conclusion_row_import_label="Import réseau",
        conclusion_row_export_label="Export réseau",
        conclusion_row_consumption_label="Consommation appareils",
        conclusion_row_total_consumption_label="Consommation totale estimée",
        conclusion_row_untracked_consumption_label="Consommation non suivie",
        conclusion_hint="Pour approfondir l'évolution temporelle et comparer les périodes, référez-vous au tableau de bord EcoPilot.",
        conclusion_comparison_insight="Écart vs {label} : consommation totale estimée {total_delta} ({total_variation}), import réseau {import_delta}, export réseau {export_delta}.",
        advice_section_title="Les conseils personnalisés EcoPilot",
        footer_path="Chemin du fichier : {path}",
        footer_page="Page {current} sur {total}",
        footer_generated="Généré le {timestamp}",
        table_empty="Aucune donnée disponible",
        bucket_labels={"hour": "heure", "day": "jour", "month": "mois"},
        period_labels={"day": "jour", "week": "semaine", "month": "mois"},
        notification_title="Rapport énergie",
        notification_line_period="Rapport énergie généré pour la période du {start} au {end}.",
        notification_line_dashboard="Tableau de bord : {dashboard}",
        notification_line_download="[Télécharger le rapport]({url})",
        notification_line_file="Fichier : {path}",
    ),
    "en": ReportTranslations(
        language="en",
        pdf_title="Energy Report",
        cover_subtitle="Energy report from {start} to {end}",
        cover_period="Period: {period}",
        cover_dashboard="Energy dashboard: {dashboard}",
        cover_bucket="Statistics granularity: {bucket}",
        cover_stats="Included statistics: {count}",
        cover_generated="Report generated on: {timestamp}",
        summary_title="Overall summary",
        summary_intro="This section presents the consolidated totals for the analysed period.",
        summary_table_title="Summary by category",
        summary_headers=("Category", "Total", "Unit"),
        summary_row_total_consumption_label="Estimated total consumption",
        summary_row_untracked_consumption_label="Untracked consumption",
        summary_note_totals="Totals correspond to the variation measured in the Energy dashboard over the selected period.",
        summary_note_negative="Negative values indicate exported energy or compensation.",
        detail_title="Breakdown by category/source",
        detail_intro="Each tracked statistic is listed with its energy to help analyse the data by origin or consumption type.",
        detail_table_title="Statistic details",
        detail_headers=("Category", "Statistic", "Energy total", "Unit"),
        chart_intro="The following chart highlights the distribution of flows per category and illustrates the production versus consumption balance.",
        chart_title="Breakdown by category",
        chart_units="Units: {unit}",
        price_section_title="Energy finances",
        price_section_intro="This section summarises the expenses and income reported by your financial sensors.",
        price_table_title="Costs and compensations",
        price_table_headers=("Source", "Total", "Type"),
        price_expense_label="Expense",
        price_income_label="Income",
        price_balance_sentence="Total expenses: {expenses} • Income: {income} • Net balance: {balance}.",
        price_sensor_labels={
            "price_electricity_import": "Electricity import cost",
            "price_electricity_export": "Electricity export compensation",
            "price_gas": "Gas cost",
            "price_water": "Water cost",
        },
        co2_section_title="CO₂",
        co2_section_intro="This section summarises the CO₂ emissions and savings reported by your sensors.",
        co2_table_title="CO₂ emissions and savings",
        co2_table_headers=("Source", "Total (kgCO₂e)", "Impact"),
        co2_emission_label="Emission",
        co2_savings_label="Saving",
        co2_balance_sentence="Total emissions: {emissions} • Savings: {savings} • Net balance: {balance}.",
        co2_sensor_labels={

            "co2_electricity": "Electricity (scope 2)",
            "co2_gas": "Gas",
            "co2_water": "Water",
            "co2_savings": "Solar self-consumption savings",

        },
        comparison_section_title="Period comparison",
        comparison_table_title="Comparison overview",
        comparison_header_category="Category",
        comparison_header_difference="Difference",
        comparison_header_variation="Change",
        comparison_consumption_label="Consumption",
        comparison_battery_charge_label="Battery charge",
        comparison_battery_discharge_label="Battery discharge",
        comparison_total_estimated_consumption_label="Estimated total consumption",
        comparison_untracked_consumption_label="Untracked consumption",
        comparison_device_consumption_label="Device consumption",
        comparison_production_label="Production",
        comparison_import_label="Grid import",
        comparison_export_label="Grid export",
        comparison_self_consumption_label="Self-consumption",
        comparison_expense_label="Expenses",
        comparison_income_label="Income",
        comparison_co2_label="CO₂",
        comparison_water_consumption_label="Water consumption",
        comparison_gas_consumption_label="Gas / fuel consumption",
        conclusion_title="Conclusion",
        conclusion_overview_without_battery="Over the period, solar production reached {production} with {direct} consumed directly. Grid imports totalled {imported} while {exported} were sent back, and devices used {consumption}. Estimated total consumption reached {total_consumption} with {untracked_consumption} untracked.",
        conclusion_overview_with_battery="Over the period, solar production reached {production}: {direct} were consumed directly and {indirect} via the battery. Grid imports totalled {imported} while {exported} were sent back, and devices used {consumption}. Estimated total consumption reached {total_consumption} with {untracked_consumption} untracked.",
        conclusion_table_title="Energy flow overview",
        conclusion_table_headers=("Flow", "Total"),
        conclusion_row_direct_label="Direct self-consumption",
        conclusion_row_indirect_label="Indirect self-consumption",
        conclusion_row_production_label="Solar production",
        conclusion_row_import_label="Grid import",
        conclusion_row_export_label="Grid export",
        conclusion_row_consumption_label="Device consumption",
        conclusion_row_total_consumption_label="Estimated total consumption",
        conclusion_row_untracked_consumption_label="Untracked consumption",
        conclusion_hint="For deeper time-based analysis and comparisons, refer to EcoPilot's dashboard.",
        conclusion_comparison_insight="Gap vs {label}: estimated total consumption {total_delta} ({total_variation}), grid import {import_delta}, grid export {export_delta}.",
        advice_section_title="EcoPilot tailored advice",
        footer_path="File path: {path}",
        footer_page="Page {current} of {total}",
        footer_generated="Generated on {timestamp}",
        table_empty="No data available",
        bucket_labels={"hour": "hour", "day": "day", "month": "month"},
        period_labels={"day": "day", "week": "week", "month": "month"},
        notification_title="Energy report",
        notification_line_period="Energy report generated for {start} to {end}.",
        notification_line_dashboard="Dashboard: {dashboard}",
        notification_line_download="[Download the report]({url})",
        notification_line_file="File: {path}",
    ),
    "nl": ReportTranslations(
        language="nl",
        pdf_title="Energiarapport",
        cover_subtitle="Energiarapport van {start} tot {end}",
        cover_period="Periode: {period}",
        cover_dashboard="Energiadashboard: {dashboard}",
        cover_bucket="Granulariteit van statistieken: {bucket}",
        cover_stats="Aantal statistieken: {count}",
        cover_generated="Rapport gegenereerd op: {timestamp}",
        summary_title="Samenvatting",
        summary_intro="Deze sectie toont de totale waarden voor de geanalyseerde periode.",
        summary_table_title="Overzicht per categorie",
        summary_headers=("Categorie", "Totaal", "Eenheid"),
        summary_row_total_consumption_label="Geschat totaalverbruik",
        summary_row_untracked_consumption_label="Niet-opgevolgd verbruik",
        summary_note_totals="De totalen komen overeen met de verandering die in het Energiadashboard is gemeten tijdens de geselecteerde periode.",
        summary_note_negative="Negatieve waarden geven geëxporteerde energie of compensatie weer.",
        detail_title="Analyse per categorie / bron",
        detail_intro="Elke gevolgde statistiek toont het energieverbruik zodat je gedetailleerd per oorsprong of verbruikstype kan analyseren.",
        detail_table_title="Statistiekdetails",
        detail_headers=("Categorie", "Statistiek", "Energietotaal", "Eenheid"),
        chart_intro="De volgende visualisatie toont de verdeling van de stromen per categorie en beeldt het evenwicht tussen productie en verbruik uit.",
        chart_title="Verdeling per categorie",
        chart_units="Eenheden: {unit}",
        price_section_title="Energiekosten en opbrengsten",
        price_section_intro="Deze sectie geeft een overzicht van de uitgaven en inkomsten die door je financiële sensoren worden gemeld.",
        price_table_title="Kosten en compensaties",
        price_table_headers=("Bron", "Totaal", "Type"),
        price_expense_label="Kost",
        price_income_label="Opbrengst",
        price_balance_sentence="Totale kosten: {expenses} • Opbrengsten: {income} • Nettoresultaat: {balance}.",
        price_sensor_labels={
            "price_electricity_import": "Kost elektriciteit (import)",
            "price_electricity_export": "Compensatie elektriciteit export",
            "price_gas": "Kost gas",
            "price_water": "Kost water",
        },
        co2_section_title="CO₂",
        co2_section_intro="Deze sectie toont de door uw sensoren geregistreerde CO₂-uitstoot en besparingen.",
        co2_table_title="CO₂-uitstoot en besparingen",
        co2_table_headers=("Bron", "Totaal (kgCO₂e)", "Impact"),
        co2_emission_label="Uitstoot",
        co2_savings_label="Besparing",
        co2_balance_sentence="Totale uitstoot: {emissions} • Besparingen: {savings} • Nettoresultaat: {balance}.",
        co2_sensor_labels={

            "co2_electricity": "Elektriciteit (scope 2)",
            "co2_gas": "Gas",
            "co2_water": "Water",
            "co2_savings": "Zonnebesparing (eigen verbruik)",

        },
        comparison_section_title="Periodevergelijking",
        comparison_table_title="Vergelijkingsoverzicht",
        comparison_header_category="Categorie",
        comparison_header_difference="Verschil",
        comparison_header_variation="Verandering",
        comparison_consumption_label="Verbruik",
        comparison_battery_charge_label="Batterij laden",
        comparison_battery_discharge_label="Batterij ontladen",
        comparison_total_estimated_consumption_label="Geschat totaalverbruik",
        comparison_untracked_consumption_label="Niet-opgevolgd verbruik",
        comparison_device_consumption_label="Apparaatverbruik",
        comparison_production_label="Productie",
        comparison_import_label="Netimport",
        comparison_export_label="Netexport",
        comparison_self_consumption_label="Eigen verbruik",
        comparison_expense_label="Kosten",
        comparison_income_label="Opbrengsten",
        comparison_co2_label="CO₂",
        comparison_water_consumption_label="Waterverbruik",
        comparison_gas_consumption_label="Gas/mazoutverbruik",
        conclusion_title="Conclusie",
        conclusion_overview_without_battery="In de periode bedroeg de zonneproductie {production} waarvan {direct} direct werd zelfverbruikt. Netimport kwam uit op {imported} terwijl {exported} werd teruggeleverd en toestellen verbruikten {consumption}. De geschatte totale consumptie bedraagt {total_consumption}, waarvan {untracked_consumption} niet gevolgd.",
        conclusion_overview_with_battery="In de periode bedroeg de zonneproductie {production}: {direct} werd rechtstreeks verbruikt en {indirect} via de batterij. Netimport bedroeg {imported} terwijl {exported} werd teruggeleverd en toestellen verbruikten {consumption}. De geschatte totale consumptie bedraagt {total_consumption}, waarvan {untracked_consumption} niet gevolgd.",
        conclusion_table_title="Overzicht energiestromen",
        conclusion_table_headers=("Stroom", "Totaal"),
        conclusion_row_direct_label="Direct eigen verbruik",
        conclusion_row_indirect_label="Indirect eigen verbruik",
        conclusion_row_production_label="Zonneproductie",
        conclusion_row_import_label="Netimport",
        conclusion_row_export_label="Netexport",
        conclusion_row_consumption_label="Verbruik toestellen",
        conclusion_row_total_consumption_label="Geschatte totale consumptie",
        conclusion_row_untracked_consumption_label="Niet gevolgde consumptie",
        conclusion_hint="Raadpleeg het Energiadashboard van EcoPilot voor een diepere tijdsanalyse en vergelijkingen.",
        conclusion_comparison_insight="Verschil t.o.v. {label}: geschat totaalverbruik {total_delta} ({total_variation}), netimport {import_delta}, netexport {export_delta}.",
        advice_section_title="EcoPilot persoonlijk advies",
        footer_path="Bestandspad: {path}",
        footer_page="Pagina {current} van {total}",
        footer_generated="Gegenereerd op {timestamp}",
        table_empty="Geen gegevens beschikbaar",
        bucket_labels={"hour": "uur", "day": "dag", "month": "maand"},
        period_labels={"day": "dag", "week": "week", "month": "maand"},
        notification_title="Energiarapport",
        notification_line_period="Energiarapport gegenereerd voor {start} tot {end}.",
        notification_line_dashboard="Dashboard: {dashboard}",
        notification_line_download="[Rapport downloaden]({url})",
        notification_line_file="Bestand: {path}",
    ),
}


def get_report_translations(language: str) -> ReportTranslations:
    """Retourner les traductions associées à la langue demandée."""

    return _TRANSLATIONS.get(language, _TRANSLATIONS[DEFAULT_LANGUAGE])


__all__ = ["ReportTranslations", "get_report_translations"]
