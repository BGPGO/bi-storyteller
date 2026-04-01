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

COLOR_PRIMARY   = (36, 76, 90)
COLOR_ACCENT    = (242, 200, 17)
COLOR_TEXT      = (40, 40, 40)
COLOR_MUTED     = (110, 110, 110)
COLOR_SECTION   = (20, 60, 75)

ANALYSIS_PROMPT = """Você é um CFO e analista de negócios sênior. Analise este dashboard de BI e produza um relatório executivo estruturado em português brasileiro.

FORMATO OBRIGATÓRIO — use exatamente estas seções com estes títulos:

RESUMO EXECUTIVO
[2-3 frases sintetizando a situação geral com os números mais relevantes visíveis]

INDICADORES-CHAVE
- [KPI 1]: [valor exato visível] — [interpretação em 1 linha]
- [KPI 2]: [valor exato visível] — [interpretação em 1 linha]
[liste todos os KPIs/métricas visíveis]

TENDÊNCIAS E DESTAQUES
[1-2 parágrafos sobre variações, crescimentos ou quedas identificados nos gráficos]

PONTOS DE ATENÇÃO
- [item 1 que requer ação ou monitoramento]
- [item 2 se houver]

RECOMENDAÇÕES
- [ação concreta baseada nos dados]
- [ação concreta baseada nos dados]

REGRAS:
- Use apenas dados visíveis na imagem. Nunca invente números.
- Se um valor não estiver legível, omita-o.
- Linguagem direta, sem rodeios, para tomada de decisão rápida.
- Página analisada: {page_name}
"""


def _safe(text: str) -> str:
    """Encode to latin-1 safely for fpdf2 built-in fonts."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _parse_sections(text: str) -> list[dict]:
    """
    Parse the structured response into a list of sections.
    Returns: [{"title": str, "lines": [str]}]
    """
    SECTION_TITLES = {
        "RESUMO EXECUTIVO", "INDICADORES-CHAVE", "TENDÊNCIAS E DESTAQUES",
        "PONTOS DE ATENÇÃO", "RECOMENDAÇÕES",
    }
    sections = []
    current_title = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                current_lines.append("")  # preserve paragraph breaks
            continue

        # Normalise for matching (strip accents roughly)
        normalised = line.upper().replace("Ç", "C").replace("Ã", "A").replace("Õ", "O") \
                         .replace("Ê", "E").replace("É", "E").replace("Í", "I") \
                         .replace("Ó", "O").replace("Ú", "U").replace("Â", "A")

        matched_title = None
        for title in SECTION_TITLES:
            norm_title = title.replace("Ç", "C").replace("Ã", "A").replace("Ã", "A") \
                              .replace("Ê", "E").replace("É", "E").replace("Í", "I") \
                              .replace("Ó", "O").replace("Ú", "U").replace("Â", "A")
            if normalised.startswith(norm_title):
                matched_title = title
                break

        if matched_title:
            if current_title is not None:
                sections.append({"title": current_title, "lines": current_lines})
            current_title = matched_title
            current_lines = []
        else:
            current_lines.append(line)

    if current_title is not None:
        sections.append({"title": current_title, "lines": current_lines})

    # Fallback: if no sections parsed, treat entire text as one block
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
        return f"Não foi possível gerar a análise desta página: {e}"


class StorytellingPDF(FPDF):
    """Branded executive PDF."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=22)

    def _header_bar(self):
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 14, "F")
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 14, 210, 2.5, "F")

    def _footer_bar(self):
        self.set_y(-14)
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, self.get_y(), 210, 14, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 7)
        now = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 14, f"BI Storyteller  |  Relatório gerado por IA  |  {now}", align="C")

    def cover_page(self, report_name: str, page_count: int):
        self.add_page()

        # Full dark background
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 297, "F")

        # Accent stripe
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 110, 210, 3, "F")

        # Tagline
        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "", 10)
        self.set_xy(0, 78)
        self.cell(210, 8, "RELATORIO EXECUTIVO DE BUSINESS INTELLIGENCE", align="C")

        # Main title
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 26)
        self.set_xy(20, 88)
        safe_name = _safe(report_name)
        self.multi_cell(170, 12, safe_name, align="C")

        # Subtitle
        self.set_font("Helvetica", "", 12)
        self.set_text_color(200, 220, 225)
        self.set_xy(0, 120)
        self.cell(210, 8, "Analise com Storytelling por Inteligencia Artificial", align="C")

        # Meta info box
        self.set_fill_color(20, 55, 68)
        self.rect(55, 148, 100, 36, "F")
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(55, 148, 3, 36, "F")

        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(62, 154)
        self.cell(0, 5, "GERADO EM")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 11)
        self.set_xy(62, 160)
        self.cell(0, 6, datetime.now().strftime("%d/%m/%Y  as  %H:%M"))

        self.set_text_color(*COLOR_ACCENT)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(62, 170)
        self.cell(0, 5, "PAGINAS ANALISADAS")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 11)
        self.set_xy(62, 176)
        self.cell(0, 6, str(page_count))

    def add_page_section(self, page_name: str, narrative: str, screenshot: Optional[bytes] = None):
        self.add_page()
        self._header_bar()
        self.ln(20)

        # Page title
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*COLOR_SECTION)
        self.set_x(12)
        self.cell(0, 10, _safe(page_name), new_x="LMARGIN", new_y="NEXT")

        # Accent underline
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(12, self.get_y(), 50, 1.2, "F")
        self.ln(6)

        # Screenshot
        if screenshot:
            try:
                self.image(io.BytesIO(screenshot), x=12, w=186)
                self.ln(6)
            except Exception as e:
                logger.warning("Could not embed screenshot: %s", e)

        # Render structured sections
        sections = _parse_sections(narrative)
        for section in sections:
            self._render_section(section["title"], section["lines"])

        self._footer_bar()

    def _render_section(self, title: str, lines: list[str]):
        if title:
            # Section header background pill
            self.set_fill_color(*COLOR_PRIMARY)
            y = self.get_y()
            self.rect(12, y, 186, 7, "F")
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 8)
            self.set_xy(15, y + 0.5)
            self.cell(0, 6, _safe(title))
            self.ln(9)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                self.ln(2)
                continue

            is_bullet = stripped.startswith("-") or stripped.startswith("•")

            if is_bullet:
                content = stripped.lstrip("-•").strip()
                # Bullet dot
                self.set_fill_color(*COLOR_ACCENT)
                self.rect(14, self.get_y() + 2.5, 2, 2, "F")
                self.set_font("Helvetica", "", 9.5)
                self.set_text_color(*COLOR_TEXT)
                self.set_x(19)
                self.multi_cell(177, 5.5, _safe(content))
            else:
                self.set_font("Helvetica", "", 9.5)
                self.set_text_color(*COLOR_TEXT)
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
