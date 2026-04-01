"""
Generates executive narrative PDFs from Power BI screenshots using Claude Vision + fpdf2.
"""

import base64
import io
import logging
import os
from datetime import datetime
from typing import Callable, Optional

import anthropic
from fpdf import FPDF

from services.screenshot_service import PageScreenshot

logger = logging.getLogger(__name__)

COLOR_PRIMARY = (36, 76, 90)
COLOR_ACCENT = (242, 200, 17)
COLOR_TEXT = (50, 50, 50)

ANALYSIS_PROMPT = """Você é um analista de negócios sênior especializado em interpretar dashboards de Business Intelligence.
Analise esta página de dashboard Power BI e gere uma narrativa executiva em português brasileiro.

Diretrizes:
- Identifique os KPIs principais e seus valores visíveis
- Destaque tendências (crescimento, queda, estabilidade) mostradas nos gráficos
- Aponte pontos de atenção ou resultados positivos relevantes
- Use linguagem profissional e objetiva para C-Level
- 3 a 5 parágrafos no máximo
- Use dados concretos (números, percentuais) quando visíveis na imagem
- NÃO invente dados que não estão visíveis na imagem

Página: {page_name}
"""


async def analyze_screenshot(image_bytes: bytes, page_name: str) -> str:
    """Send a screenshot to Claude Vision and return executive narrative."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    try:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = await client.messages.create(
            model=model,
            max_tokens=1500,
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
    finally:
        await client.aclose()


class StorytellingPDF(FPDF):
    """Branded PDF with cover + per-page narrative + screenshot."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)

    def _header_bar(self):
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, 210, 12, "F")
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(0, 12, 210, 2, "F")

    def _footer_bar(self):
        self.set_y(-15)
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, self.get_y() + 5, 210, 10, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 10, "Relatorio gerado por BI Storyteller com IA", align="C")

    def cover_page(self, report_name: str):
        self.add_page()
        self._header_bar()

        self.set_y(80)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 15, "Relatorio Executivo", new_x="LMARGIN", new_y="NEXT", align="C")

        self.set_font("Helvetica", "", 14)
        self.set_text_color(*COLOR_TEXT)
        self.cell(0, 10, "Analise com Storytelling por IA", new_x="LMARGIN", new_y="NEXT", align="C")

        self.ln(8)
        self.set_fill_color(*COLOR_ACCENT)
        self.rect(70, self.get_y(), 70, 1, "F")

        self.ln(15)
        self.set_font("Helvetica", "", 12)
        safe_name = report_name.encode("latin-1", errors="replace").decode("latin-1")
        self.cell(0, 8, safe_name, new_x="LMARGIN", new_y="NEXT", align="C")

        now = datetime.now().strftime("%d/%m/%Y as %H:%M")
        self.cell(0, 8, f"Gerado em {now}", new_x="LMARGIN", new_y="NEXT", align="C")

        self._footer_bar()

    def add_page_section(self, page_name: str, narrative: str, screenshot: Optional[bytes] = None):
        self.add_page()
        self._header_bar()
        self.ln(18)

        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*COLOR_PRIMARY)
        safe_name = page_name.encode("latin-1", errors="replace").decode("latin-1")
        self.cell(0, 10, safe_name, new_x="LMARGIN", new_y="NEXT")

        self.set_fill_color(*COLOR_ACCENT)
        self.rect(10, self.get_y(), 40, 1, "F")
        self.ln(5)

        if screenshot:
            try:
                self.image(io.BytesIO(screenshot), x=10, w=190)
                self.ln(5)
            except Exception as e:
                logger.warning("Could not embed screenshot: %s", e)

        self.set_font("Helvetica", "", 10)
        self.set_text_color(*COLOR_TEXT)
        safe_text = narrative.encode("latin-1", errors="replace").decode("latin-1")
        self.multi_cell(0, 6, safe_text)

        self._footer_bar()


async def generate_storytelling_pdf(
    screenshots: list[PageScreenshot],
    report_name: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> bytes:
    """
    Build a storytelling PDF from screenshots.

    For each page: Claude Vision generates narrative → embed screenshot + text in PDF.
    """
    total = len(screenshots)
    pdf = StorytellingPDF()
    pdf.cover_page(report_name)

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
    """
    Build a one-page storytelling PDF from a single screenshot (Screen Capture mode).
    """
    shot = PageScreenshot(page_name=page_name, page_index=0, image_bytes=image_bytes)
    return await generate_storytelling_pdf([shot], report_name)
