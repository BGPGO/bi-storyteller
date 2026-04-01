"""
Export routes:
  POST /api/export/page     — Analyze a screenshot from Screen Capture API → PDF (sync)
  POST /api/export/full     — Start async Playwright capture of all report pages → job_id
  GET  /api/export/status/{job_id}   — Poll job progress
  GET  /api/export/download/{job_id} — Download completed PDF
"""

import asyncio
import base64
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.job_manager import JobStatus, job_manager
from services.screenshot_service import capture_report_pages
from services.storytelling_service import generate_pdf_from_image, generate_storytelling_pdf

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class PageExportRequest(BaseModel):
    """Export current page using screenshot from Screen Capture API."""
    screenshot: str           # base64 PNG
    report_name: str = "Relatorio"
    page_name: str = "Pagina atual"


class FullExportRequest(BaseModel):
    """Start full-report export using Playwright."""
    url: str
    report_name: str = "Relatorio"


# ── Page export (sync, from Screen Capture) ───────────────────────────────────

@router.post("/page", summary="Gera PDF da página atual (screenshot do frontend)")
async def export_page(body: PageExportRequest):
    """
    Receives a base64 PNG screenshot captured by the frontend (Screen Capture API),
    analyzes it with Claude Vision, and returns a PDF directly.
    """
    try:
        image_bytes = base64.b64decode(body.screenshot)
    except Exception:
        raise HTTPException(status_code=400, detail="Screenshot inválido (base64 mal formado)")

    try:
        pdf_bytes = await generate_pdf_from_image(
            image_bytes=image_bytes,
            report_name=body.report_name,
            page_name=body.page_name,
        )
    except Exception as e:
        logger.exception("Failed to generate page PDF: %s", e)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{body.report_name}.pdf"'},
    )


# ── Full export (async, Playwright) ──────────────────────────────────────────

async def _run_full_export(job_id: str, url: str, report_name: str):
    """Background task: Playwright capture → Claude Vision → PDF."""
    try:
        job_manager.update_progress(job_id, 0, "Abrindo relatório no Playwright...")

        def on_capture(page_idx: int, total: int, page_name: str):
            job_manager.update_progress(
                job_id,
                page_idx,
                f"Capturando {page_name} ({page_idx + 1}/{total})",
            )

        screenshots = await capture_report_pages(url, on_progress=on_capture)

        if not screenshots:
            job_manager.fail_job(job_id, "Nenhuma página capturada — verifique a URL")
            return

        job = job_manager.get_job(job_id)
        if job:
            job.total_steps = len(screenshots) * 2  # capture + analysis per page

        def on_analysis(step_idx: int, total: int, step_desc: str):
            captured = total  # screenshots already done
            job_manager.update_progress(job_id, captured + step_idx, step_desc)

        pdf_bytes = await generate_storytelling_pdf(
            screenshots=screenshots,
            report_name=report_name,
            on_progress=on_analysis,
        )

        job_manager.complete_job(job_id, pdf_bytes)
        logger.info("Full export job %s completed (%d bytes)", job_id, len(pdf_bytes))

    except Exception as e:
        logger.exception("Full export job %s failed: %s", job_id, e)
        job_manager.fail_job(job_id, str(e))


@router.post("/full", summary="Inicia exportação completa do relatório (assíncrono)")
async def start_full_export(body: FullExportRequest):
    """
    Starts a background job that:
    1. Opens the Power BI URL with Playwright
    2. Navigates through all pages and takes screenshots
    3. Analyzes each screenshot with Claude Vision
    4. Generates a PDF with narratives + images

    Returns job_id for polling via GET /status/{job_id}.
    """
    job_manager.cleanup_old_jobs()
    job = job_manager.create_job(total_steps=1)

    asyncio.create_task(
        _run_full_export(
            job_id=job.id,
            url=body.url,
            report_name=body.report_name,
        )
    )

    return {"job_id": job.id, "status": "queued"}


@router.get("/status/{job_id}", summary="Status do job de exportação")
async def get_export_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job.to_dict()


@router.get("/download/{job_id}", summary="Download do PDF gerado")
async def download_export(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job ainda não concluído (status: {job.status.value})",
        )

    pdf_bytes = job_manager.get_file(job_id)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="Arquivo não encontrado")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="storytelling_{job_id}.pdf"'},
    )
