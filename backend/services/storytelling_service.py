"""
Generates executive narrative PDFs from Power BI screenshots using Claude Vision + fpdf2.
"""

import base64
import io
import logging
import os
import re
from datetime import datetime
from typing import Callable, Optional

import anthropic
from fpdf import FPDF

from services.screenshot_service import PageScreenshot

logger = logging.getLogger(__name__)

# BGP brand colors
COLOR_PRIMARY = (36, 76, 90)       # #244C5A — dark teal
COLOR_ACCENT  = (171, 199, 201)    # #ABC7C9 — light blue
COLOR_TEXT    = (35, 35, 35)
COLOR_MUTED   = (100, 100, 100)
COLOR_WHITE   = (255, 255, 255)

ANALYSIS_PROMPT = """Você é um CFO e analista de negócios sênior da BGP GO - Expertise Financeira.
Analise este dashboard de Business Intelligence e produza um relatório executivo estruturado em português brasileiro.

FORMATO OBRIGATÓRIO — use exatamente estas seções com estes títulos (sem ## ou qualquer marcação):

RESUMO EXECUTIVO
[2-3 frases sintetizando a situação geral com os números mais relevantes visíveis]

INDICADORES-CHAVE
- [KPI 1]: [valor exato visível] - [interpretação em 1 linha]
- [KPI 2]: [valor exato visível] - [interpretação em 1 linha]
[liste todos os KPIs e métricas visíveis no dashboard]

TENDENCIAS E DESTAQUES
[1-2 parágrafos sobre variações, crescimentos ou quedas identificados nos gráficos]

PONTOS DE ATENCAO
- [item concreto que requer ação ou monitoramento]
- [outro item se houver]

RECOMENDACOES
- [ação concreta baseada nos dados visíveis]
- [ação concreta baseada nos dados visíveis]

REGRAS ABSOLUTAS:
- Use apenas dados visíveis na imagem. Nunca invente ou estime números.
- NÃO use marcações markdown como **, ## ou *.
- Use traço simples (-) como separador nas listas, nunca seta ou símbolo especial.
- Se um valor não estiver legível, omita-o completamente.
- Linguagem direta e objetiva para tomada de decisão rápida.
- Página analisada: {page_name}
"""

SECTION_TITLES = [
    "RESUMO EXECUTIVO",
    "INDICADORES-CHAVE",
    "TENDENCIAS E DESTAQUES",
    "PONTOS DE ATENCAO",
    "RECOMENDACOES",
]


def _safe(text: str) -> str:
    """Clean and encode text to latin-1 for fpdf2 built-in fonts."""
    # Replace common unicode symbols with ascii equivalents
    replacements = {
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...",
        "\u2192": "->", "\u2190": "<-", "\u2022": "-",
        "\u00b7": "-", "**": "", "##": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _normalise(text: str) -> str:
    """Normalise accents for section title matching."""
    return (
        text.upper()
        .replace("Ç", "C").replace("Ã", "A").replace("Â", "A")
        .replace("Ê", "E").replace("É", "E").replace("È", "E")
        .replace("Í", "I").replace("Ó", "O").replace("Ô", "O")
        .replace("Ú", "U").replace("Ü", "U")
        .strip()
    )


def _parse_sections(text: str) -> list[dict]:
    """Parse structured Claude output into sections."""
    sections: list[dict] = []
    current_title: Optional[str] = None
    current_lines: list[str] = []

    for raw in text.splitlines():
        # Strip markdown artifacts
        line = raw.strip().lstrip("#").strip()
        if not line:
            if current_lines and current_lines[-1] != "":
                current_lines.append("")
            continue

        norm = _normalise(line)
        matched = next((t for t in SECTION_TITLES if norm.startswith(t)), None)

        if matched:
            if current_title is not None:
                sections.append({"title": current_title, "lines": current_lines})
            current_title = matched
            current_lines = []
        else:
            current_lines.append(line)

    if current_title is not None:
        sections.append({"title": current_title, "lines": current_lines})

    if not sections:
        sections = [{"title": "", "lines": text.splitlines()}]

    return sections


async def analyze_screenshot(image_bytes: bytes, page_name: str) -> str:
    """Send a screenshot to Claude Vision and return structured executive narrative."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = await client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64},
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT.format(page_name=page_name),
                    },
                ],
            }],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error("Claude Vision error for page '%s': %s", page_name, e)
        return f"Nao foi possivel gerar a analise desta pagina: {e}"


class StorytellingPDF(FPDF):
    """BGP-branded executive PDF."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=22)

    # ── Chrome ───────────────────────────────────────────────────────────────

    def _header_bar(self):
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 14, "F")
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 14, 210, 2, "F")

    def _footer_bar(self):
        self.set_y(-13)
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, self.get_y(), 210, 13, "F")
        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "", 7)
        now = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 13, f"BGP GO - Expertise Financeira  |  BI Storyteller  |  {now}", align="C")

    # ── Cover ────────────────────────────────────────────────────────────────

    def cover_page(self, report_name: str, page_count: int):
        self.add_page()

        # Background
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 297, "F")

        # Accent horizontal stripe
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 120, 210, 2, "F")

        # Left accent bar
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 0, 4, 297, "F")

        # Label
        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(20, 75)
        self.cell(0, 6, "RELATORIO EXECUTIVO DE BUSINESS INTELLIGENCE")

        # Report name
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 24)
        self.set_xy(20, 85)
        self.multi_cell(175, 11, _safe(report_name))

        # Sub
        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "", 11)
        self.set_xy(20, self.get_y() + 4)
        self.cell(0, 7, "Analise com Storytelling por Inteligencia Artificial")

        # Info box
        box_y = 135
        self.set_fill_color(25, 60, 74)
        self.rect(20, box_y, 80, 32, "F")
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(20, box_y, 3, 32, "F")

        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "B", 7)
        self.set_xy(27, box_y + 5)
        self.cell(0, 4, "DATA DE GERACAO")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "", 10)
        self.set_xy(27, box_y + 11)
        self.cell(0, 5, datetime.now().strftime("%d/%m/%Y  %H:%M"))

        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "B", 7)
        self.set_xy(27, box_y + 20)
        self.cell(0, 4, "TELAS ANALISADAS")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "", 10)
        self.set_xy(27, box_y + 26)
        self.cell(0, 5, str(page_count))

    # ── Content page ─────────────────────────────────────────────────────────

    def add_page_section(self, page_name: str, narrative: str, screenshot: Optional[bytes] = None):
        self.add_page()
        self._header_bar()
        self.ln(20)

        # Page title
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*COLOR_PRIMARY)
        self.set_x(12)
        self.cell(0, 9, _safe(page_name), new_x="LMARGIN", new_y="NEXT")

        # Accent underline
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(12, self.get_y(), 60, 1.5, "F")
        self.ln(7)

        # Screenshot
        if screenshot:
            try:
                self.image(io.BytesIO(screenshot), x=12, w=186)
                self.ln(6)
            except Exception as e:
                logger.warning("Could not embed screenshot: %s", e)

        # Structured content
        for section in _parse_sections(narrative):
            self._render_section(section["title"], section["lines"])

        self._footer_bar()

    def _render_section(self, title: str, lines: list[str]):
        if title:
            # Section header pill
            y = self.get_y()
            self.set_fill_color(*COLOR_PRIMARY)
            self.rect(12, y, 186, 7, "F")
            self.set_fill_color(*COLOR_ACCENT)
            self.rect(12, y, 3, 7, "F")
            self.set_text_color(*COLOR_WHITE)
            self.set_font("Helvetica", "B", 8)
            self.set_xy(18, y + 1)
            self.cell(0, 5, _safe(title))
            self.ln(10)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                self.ln(2)
                continue

            is_bullet = stripped.startswith("-") or stripped.startswith("•")

            if is_bullet:
                content = stripped.lstrip("-•").strip()
                # Bullet dot
                bx, by = 15, self.get_y() + 2.2
                self.set_fill_color(*COLOR_ACCENT)
                self.rect(bx, by, 2, 2, "F")
                self.set_text_color(*COLOR_TEXT)
                self.set_font("Helvetica", "", 9.5)
                self.set_x(20)
                self.multi_cell(176, 5.5, _safe(content))
            else:
                self.set_text_color(*COLOR_TEXT)
                self.set_font("Helvetica", "", 9.5)
                self.set_x(12)
                self.multi_cell(186, 5.5, _safe(stripped))

        self.ln(3)


async def generate_storytelling_pdf(
    screenshots: list[PageScreenshot],
    report_name: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> bytes:
    total = len(screenshots)
    pdf = StorytellingPDF()
    pdf.cover_page(report_name, total)

    for i, shot in enumerate(screenshots):
        step = f"Analisando {shot.page_name} ({i + 1}/{total})"
        logger.info(step)
        if on_progress:
            on_progress(i, total, step)

        narrative = await analyze_screenshot(shot.image_bytes, shot.page_name)
        pdf.add_page_section(
            page_name=shot.page_name,
            narrative=narrative,
            screenshot=shot.image_bytes,
        )

    logger.info("PDF generated: %d pages", total)
    return bytes(pdf.output())


async def generate_pdf_from_image(
    image_bytes: bytes,
    report_name: str = "Relatorio",
    page_name: str = "Pagina atual",
) -> bytes:
    shot = PageScreenshot(page_name=page_name, page_index=0, image_bytes=image_bytes)
    return await generate_storytelling_pdf([shot], report_name)
