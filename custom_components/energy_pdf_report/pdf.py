"""Génération de rapports PDF pour l'intégration energy_pdf_report."""

import base64
import zlib
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from fpdf import FPDF

from .font_data import FONT_DATA

from .translations import ReportTranslations


FONT_FAMILY = "DejaVuSans"
_FONT_FILES: Dict[str, str] = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
}

PRIMARY_COLOR = (46, 134, 193)
HEADER_TEXT_COLOR = (255, 255, 255)
TEXT_COLOR = (33, 37, 41)
LIGHT_TEXT_COLOR = (110, 117, 126)
BORDER_COLOR = (222, 230, 236)
ZEBRA_COLORS = ((255, 255, 255), (245, 249, 252))
TOTAL_FILL_COLOR = (235, 239, 243)
TOTAL_TEXT_COLOR = (87, 96, 106)
SECTION_SPACING = 9
SECTION_TITLE_SPACING = 4
TABLE_BOTTOM_SPACING = 3

CHART_BACKGROUND = (245, 249, 253)
BAR_TRACK_COLOR = (226, 235, 243)
BAR_BORDER_COLOR = (202, 214, 223)

_CATEGORY_COLORS: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (

    ("solaire", (241, 196, 15)),
    ("électricité", (52, 152, 219)),
    ("réseau", (52, 152, 219)),
    ("consommation", (46, 134, 193)),
    ("production", (39, 174, 96)),
    ("gaz", (231, 76, 60)),
    ("eau", (26, 188, 156)),
    ("batterie", (155, 89, 182)),
    ("co₂", (100, 100, 100)),
    ("co2", (100, 100, 100)),
    ("coût", (243, 156, 18)),
    ("cout", (243, 156, 18)),
    ("cost", (243, 156, 18)),
    ("compensation", (46, 204, 113)),
    ("revenu", (46, 204, 113)),
    ("income", (46, 204, 113)),
)

_CATEGORY_ICON_HINTS: Tuple[Tuple[str, str], ...] = (

    ("solaire", "☀"),
    ("réseau", "⚡"),
    ("électricité", "⚡"),
    ("consommation", "⚡"),
    ("appareil", "🔌"),
    ("gaz", "🔥"),
    ("eau", "💧"),
    ("batterie", "⏻"),
    ("co₂", "🌍"),
    ("co2", "🌍"),
    ("coût", "💰"),
    ("cout", "💰"),
    ("cost", "💰"),
    ("revenu", "💶"),
    ("income", "💶"),
    ("compensation", "💶"),
)


def _decode_font(encoded: str) -> bytes:
    """Décoder un flux de police compressé en bytes TTF."""

    return zlib.decompress(base64.b64decode(encoded))


class _TemporaryFontCache:
    """Stockage temporaire des polices nécessaires à FPDF."""

    def __init__(self) -> None:
        self._tempdir = TemporaryDirectory(prefix="energy_pdf_report_fonts_")
        self.directory = Path(self._tempdir.name)
        self._populate()

    def _populate(self) -> None:
        for filename, encoded in FONT_DATA.items():
            (self.directory / filename).write_bytes(_decode_font(encoded))

    def cleanup(self) -> None:
        self._tempdir.cleanup()


def _register_unicode_fonts(pdf: FPDF) -> Optional[_TemporaryFontCache]:
    """Enregistrer les polices Unicode sur le PDF et retourner le cache."""

    missing_styles = [
        style for style in _FONT_FILES if f"{FONT_FAMILY.lower()}{style}" not in pdf.fonts
    ]

    if not missing_styles:
        return None

    cache = _TemporaryFontCache()

    for style, filename in _FONT_FILES.items():
        font_key = f"{FONT_FAMILY.lower()}{style}"
        if font_key in pdf.fonts:
            continue

        pdf.add_font(FONT_FAMILY, style, str(cache.directory / filename), uni=True)

    return cache


@dataclass

class TableConfig:
    """Configuration d'un tableau à insérer dans le PDF."""

    title: str
    headers: Sequence[str]
    rows: Iterable[Sequence[str]]

    column_widths: Optional[Sequence[float]] = None
    emphasize_rows: Optional[Sequence[int]] = None
    first_column_is_category: bool = False


class EnergyReportPDF(FPDF):
    """PDF thématisé avec en-tête et pied de page personnalisés."""


    def __init__(
        self,
        title: str,
        period_label: str,
        generated_at: datetime,

        translations: ReportTranslations,
    ) -> None:
        super().__init__()
        self.report_title = title
        self.period_label = period_label
        self.generated_at = generated_at
        self.translations = translations
        self._suppress_header = False
        self._suppress_footer = False
        self.set_margins(15, 22, 15)

    def header(self) -> None:  # pragma: no cover - géré par fpdf
        if self._suppress_header:
            return

        available_width = self.w - self.l_margin - self.r_margin
        self.set_xy(self.l_margin, 12)
        self.set_fill_color(*PRIMARY_COLOR)
        self.set_text_color(*HEADER_TEXT_COLOR)
        self.set_draw_color(*PRIMARY_COLOR)
        self.set_font(FONT_FAMILY, "B", 12)
        self.cell(available_width, 8, self.report_title, border=0, ln=1, fill=True)
        self.set_font(FONT_FAMILY, "", 9)
        self.cell(available_width, 6, self.period_label, border=0, ln=1, fill=True)
        self.ln(3)
        self.set_text_color(*TEXT_COLOR)
        self.set_draw_color(*BORDER_COLOR)

    def footer(self) -> None:  # pragma: no cover - géré par fpdf
        if self._suppress_footer:
            return

        self.set_y(-15)
        self.set_font(FONT_FAMILY, "", 9)
        self.set_text_color(*LIGHT_TEXT_COLOR)
        page_text = self.translations.footer_page.format(
            current=self.page_no(), total="{nb}"
        )
        generated_text = self.translations.footer_generated.format(
            timestamp=self.generated_at.strftime("%d/%m/%Y %H:%M")
        )
        self.cell(0, 5, page_text, align="L")
        self.cell(0, 5, generated_text, align="R")
        self.set_text_color(*TEXT_COLOR)


class EnergyPDFBuilder:
    """Constructeur simplifié de rapports PDF professionnels."""

    def __init__(
        self,
        title: str,
        period_label: str,
        generated_at: datetime,
        translations: ReportTranslations,
        logo_path: Optional[Union[str, Path]] = None,
    ) -> None:
        """Initialiser le générateur de PDF."""

        self._translations = translations
        self._pdf = EnergyReportPDF(title, period_label, generated_at, translations)
        self._pdf.set_auto_page_break(auto=True, margin=18)
        self._pdf.alias_nb_pages()
        self._font_cache = _register_unicode_fonts(self._pdf)

        self._logo_path = self._validate_logo(logo_path)
        self._content_started = False
        self._pdf.set_title(title)
        self._pdf.set_creator("Home Assistant")
        self._pdf.set_author("energy_pdf_report")
        self._default_text_color = TEXT_COLOR

    @property
    def _available_width(self) -> float:
        """Retourner la largeur disponible pour le contenu."""

        return self._pdf.w - self._pdf.l_margin - self._pdf.r_margin

    def add_cover_page(
        self,
        subtitle: str,
        details: Sequence[str],

        logo_path: Optional[Union[str, Path]] = None,

    ) -> None:
        """Ajouter une page de garde élégante."""

        logo = self._validate_logo(logo_path) or self._logo_path

        self._pdf._suppress_header = True
        self._pdf._suppress_footer = True
        previous_break = self._pdf.auto_page_break
        previous_margin = self._pdf.b_margin
        self._pdf.set_auto_page_break(auto=False)
        self._pdf.add_page()

        self._pdf.set_text_color(*PRIMARY_COLOR)
        self._pdf.set_font(FONT_FAMILY, "B", 28)
        self._pdf.set_y(70)

        if logo and logo.exists():
            width = min(self._available_width * 0.6, 140)
            x_position = (self._pdf.w - width) / 2
            self._pdf.image(str(logo), x=x_position, w=width)
            self._pdf.ln(65)
        else:
            self._pdf.ln(30)

        self._pdf.cell(0, 16, self._pdf.report_title, align="C", ln=True)

        self._pdf.set_font(FONT_FAMILY, "", 14)
        self._pdf.set_text_color(*TEXT_COLOR)
        self._pdf.cell(0, 10, subtitle, align="C", ln=True)
        self._pdf.ln(10)

        self._pdf.set_font(FONT_FAMILY, "", 11)
        for line in details:
            self._pdf.cell(0, 8, line, align="C", ln=True)

        self._pdf.set_auto_page_break(auto=previous_break, margin=previous_margin)
        self._pdf._suppress_header = False
        self._pdf._suppress_footer = False
        self._content_started = False

    def add_section_title(self, text: str) -> None:
        """Ajouter un titre de section coloré."""

        self._ensure_content_page()
        self._ensure_space(10)
        self._pdf.set_text_color(*PRIMARY_COLOR)
        self._pdf.set_font(FONT_FAMILY, "B", 15)
        self._pdf.cell(0, 10, text, ln=True)
        self._pdf.ln(SECTION_TITLE_SPACING)
        self._pdf.set_text_color(*self._default_text_color)

    def add_paragraph(self, text: str, bold: bool = False, size: int = 11) -> None:
        """Ajouter un paragraphe simple."""

        self._ensure_content_page()
        font_style = "B" if bold else ""
        self._pdf.set_font(FONT_FAMILY, font_style, size)
        self._ensure_space(SECTION_SPACING)
        self._pdf.multi_cell(0, 6, text)
        self._pdf.ln(1)

    def add_table(self, config: TableConfig) -> None:
        """Ajouter un tableau structuré."""

        headers = list(config.headers)
        rows = list(config.rows)
        if not headers:
            return

        self._ensure_content_page()
        if config.column_widths is not None:
            column_widths = list(config.column_widths)
        else:
            column_widths = [self._available_width / len(headers)] * len(headers)

        header_height = 8
        row_height = 7

        decorate_first_column = config.first_column_is_category


        self._pdf.set_font(FONT_FAMILY, "B", 13)
        self._ensure_space(header_height + 6)
        self._pdf.cell(0, 9, config.title, ln=True)

        self._pdf.set_font(FONT_FAMILY, "B", 10)
        self._pdf.set_fill_color(*PRIMARY_COLOR)
        self._pdf.set_text_color(*HEADER_TEXT_COLOR)
        self._pdf.set_draw_color(*BORDER_COLOR)
        self._draw_row(headers, column_widths, header_height, fill=True)

        self._pdf.set_font(FONT_FAMILY, "", 10)
        self._pdf.set_text_color(*self._default_text_color)

        if not rows:

            empty_row = [self._translations.table_empty] + [""] * (len(headers) - 1)

            self._draw_row(empty_row, column_widths, row_height, fill=True)
            self._pdf.ln(TABLE_BOTTOM_SPACING)
            return

        emphasize = set(config.emphasize_rows or [])

        for index, row in enumerate(rows):
            str_row = ["" if value is None else str(value) for value in row]
            if decorate_first_column and str_row:
                str_row[0] = _decorate_category(str_row[0])
            fill_color = ZEBRA_COLORS[index % 2]
            text_color = self._default_text_color
            font_style = ""

            if index in emphasize:
                fill_color = TOTAL_FILL_COLOR
                text_color = TOTAL_TEXT_COLOR
                font_style = "B"

            self._draw_row(
                str_row,
                column_widths,
                row_height,
                fill=True,
                fill_color=fill_color,
                text_color=text_color,
                font_style=font_style,
            )

        self._pdf.ln(TABLE_BOTTOM_SPACING)
        self._pdf.set_text_color(*self._default_text_color)

    def add_chart(
        self,
        title: str,

        series: Sequence[Tuple[str, float, str]],
        ylabel: Optional[str] = None,
    ) -> None:

        """Dessiner un graphique en barres/gauges directement avec fpdf2."""

        if not series:
            return


        values = [value for _, value, _ in series]
        if not any(abs(value) > 1e-6 for value in values):
            return

        units = {unit for _, _, unit in series if unit}
        if ylabel is None and len(units) == 1:
            (ylabel,) = tuple(units)

        num_bars = len(series)
        bar_height = 8
        bar_spacing = 4
        padding_top = 8
        padding_bottom = 8
        chart_height = padding_top + padding_bottom + num_bars * bar_height + max(0, num_bars - 1) * bar_spacing

        self._ensure_content_page()
        self._ensure_space(chart_height + 20)
        self._pdf.set_font(FONT_FAMILY, "B", 12)
        self._pdf.cell(0, 8, title, ln=True)
        if ylabel:
            self._pdf.set_font(FONT_FAMILY, "", 9)
            self._pdf.set_text_color(*LIGHT_TEXT_COLOR)

            units_label = self._translations.chart_units.format(unit=ylabel)
            self._pdf.cell(0, 5, units_label, ln=True)

            self._pdf.set_text_color(*self._default_text_color)
        else:
            self._pdf.ln(1)

        chart_left = self._pdf.l_margin
        chart_width = self._available_width
        value_width = max(32.0, min(60.0, chart_width * 0.18))
        label_width = max(45.0, min(90.0, chart_width * 0.38))
        bar_area_width = chart_width - label_width - value_width - 8
        if bar_area_width < 70:
            label_width = max(40.0, chart_width - value_width - 70.0 - 8.0)
            bar_area_width = chart_width - label_width - value_width - 8
        if bar_area_width < 60:
            value_width = max(30.0, chart_width - label_width - 60.0 - 8.0)
            bar_area_width = chart_width - label_width - value_width - 8
        bar_area_width = max(55.0, bar_area_width)

        chart_top = self._pdf.get_y()
        self._pdf.set_fill_color(*CHART_BACKGROUND)
        self._pdf.set_draw_color(*BORDER_COLOR)
        self._pdf.rect(chart_left, chart_top, chart_width, chart_height, style="F")
        self._pdf.rect(chart_left, chart_top, chart_width, chart_height)

        bar_area_left = chart_left + label_width + 4
        positive_max = max((value for value in values if value > 0), default=0.0)
        negative_min = min((value for value in values if value < 0), default=0.0)

        if positive_max > 0 and negative_min < 0:
            total_span = positive_max + abs(negative_min)
            zero_x = bar_area_left + (abs(negative_min) / total_span) * bar_area_width
        elif positive_max > 0:
            zero_x = bar_area_left
        else:
            zero_x = bar_area_left + bar_area_width

        positive_span = bar_area_left + bar_area_width - zero_x
        negative_span = zero_x - bar_area_left
        positive_scale = positive_span / positive_max if positive_max > 0 else 0
        negative_scale = negative_span / abs(negative_min) if negative_min < 0 else 0

        self._pdf.set_draw_color(*BAR_BORDER_COLOR)
        self._pdf.line(zero_x, chart_top, zero_x, chart_top + chart_height)

        current_y = chart_top + padding_top
        for label, value, unit in series:
            track_top = current_y
            category_color = _get_category_color(label)
            self._pdf.set_fill_color(*BAR_TRACK_COLOR)
            self._pdf.rect(bar_area_left, track_top, bar_area_width, bar_height, style="F")

            if value >= 0 and positive_scale > 0:
                bar_width = max(0.5, value * positive_scale)
                self._pdf.set_fill_color(*category_color)
                self._pdf.rect(zero_x, track_top, bar_width, bar_height, style="F")
            elif value < 0 and negative_scale > 0:
                bar_width = max(0.5, abs(value) * negative_scale)
                self._pdf.set_fill_color(*category_color)
                self._pdf.rect(zero_x - bar_width, track_top, bar_width, bar_height, style="F")

            self._pdf.set_draw_color(*BAR_BORDER_COLOR)
            self._pdf.rect(bar_area_left, track_top, bar_area_width, bar_height)

            self._pdf.set_text_color(*TEXT_COLOR)
            self._pdf.set_font(FONT_FAMILY, "", 10)
            label_text = _decorate_category(label)
            self._pdf.set_xy(chart_left + 4, track_top + 1)
            self._pdf.cell(label_width - 4, bar_height - 2, label_text, align="L")

            value_text = _format_measure(value, unit)
            self._pdf.set_xy(bar_area_left + bar_area_width + 4, track_top + 1)
            self._pdf.cell(value_width, bar_height - 2, value_text, align="R")

            current_y += bar_height + bar_spacing

        self._pdf.set_y(chart_top + chart_height + 4)


    def compute_column_widths(self, weights: Sequence[float]) -> List[float]:

        """Convertir des poids relatifs en largeurs exploitables par FPDF."""

        if not weights:
            raise ValueError("Les poids de colonne ne peuvent pas être vides")

        total_weight = sum(weights)
        if total_weight <= 0:
            raise ValueError("Les poids de colonne doivent avoir une somme positive")

        available = self._available_width
        return [(weight / total_weight) * available for weight in weights]

    def add_footer(self, text: str) -> None:
        """Ajouter un texte informatif discret en fin de rapport."""

        self._ensure_content_page()
        self._pdf.set_font(FONT_FAMILY, "", 9)
        self._ensure_space(5)
        self._pdf.set_text_color(*LIGHT_TEXT_COLOR)
        self._pdf.multi_cell(0, 5, text)
        self._pdf.set_text_color(*self._default_text_color)

    def output(self, path: str) -> None:

        """Sauvegarder le PDF en garantissant le nettoyage des ressources."""

        with ExitStack() as stack:
            stack.callback(self._cleanup_resources)
            self._pdf.output(path)


    def _cleanup_resources(self) -> None:
        """Nettoyer les répertoires temporaires."""

        cache = getattr(self, "_font_cache", None)
        if cache is not None:
            cache.cleanup()
            self._font_cache = None

        assets_cache = getattr(self, "_assets_cache", None)
        if assets_cache is not None:
            assets_cache.cleanup()
            self._assets_cache = None

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        self._cleanup_resources()

    def _ensure_content_page(self) -> None:
        if not self._content_started:
            self._pdf.add_page()
            self._content_started = True

    def _draw_row(
        self,
        row: Sequence[str],
        column_widths: Sequence[float],
        height: float,
        *,
        fill: bool = False,

        fill_color: Optional[Tuple[int, int, int]] = None,
        text_color: Optional[Tuple[int, int, int]] = None,

        font_style: str = "",
    ) -> None:
        """Dessiner une ligne du tableau."""

        if fill_color is not None:
            self._pdf.set_fill_color(*fill_color)
        if text_color is not None:
            self._pdf.set_text_color(*text_color)
        self._pdf.set_font(FONT_FAMILY, font_style, 10)
        self._ensure_space(height)

        for index, (value, width) in enumerate(zip(row, column_widths)):
            align = "R" if index == len(row) - 1 else "L"
            self._pdf.cell(width, height, value, border=1, align=align, fill=fill)
        self._pdf.ln(height)

    def _ensure_space(self, height: float) -> None:
        """Ajouter une page si besoin."""

        self._ensure_content_page()
        if self._pdf.get_y() + height > self._pdf.page_break_trigger:
            self._pdf.add_page()

    def _validate_logo(self, logo_path: Optional[Union[str, Path]]) -> Optional[Path]:
        if not logo_path:
            return None
        path = Path(logo_path)
        if path.exists() and path.is_file():
            return path
        return None


def _decorate_category(label: str) -> str:
    """Ajouter une icône appropriée devant une catégorie si disponible."""

    normalized = label.strip()
    lowered = normalized.lower()
    for keyword, icon in _CATEGORY_ICON_HINTS:
        if keyword in lowered and not normalized.startswith(icon):
            return f"{icon} {normalized}"
    return normalized


def _get_category_color(label: str) -> Tuple[int, int, int]:
    """Choisir une couleur fixe en fonction de la catégorie."""

    lowered = label.lower()
    for keyword, color in _CATEGORY_COLORS:
        if keyword in lowered:
            return color
    return PRIMARY_COLOR


def _format_measure(value: float, unit: Optional[str]) -> str:
    """Formater une valeur numérique avec unité."""

    formatted = _format_number(value)
    return f"{formatted} {unit}".strip() if unit else formatted


def _format_number(value: float) -> str:
    """Formater un nombre pour l'affichage dans le PDF."""

    magnitude = abs(value)
    if magnitude >= 1000:
        formatted = f"{value:,.0f}"
    elif magnitude >= 100:
        formatted = f"{value:,.1f}"
    else:
        formatted = f"{value:,.2f}"
    return formatted.replace(",", " ")



__all__ = ["EnergyPDFBuilder", "TableConfig"]
