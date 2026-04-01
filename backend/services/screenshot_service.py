"""
Playwright-based screenshot capture for Power BI public embed URLs.
Navigates through all report pages and returns PNG screenshots.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)

RENDER_WAIT_MS = 8000
NAV_TIMEOUT_MS = 60000
VIEWPORT = {"width": 1920, "height": 1080}


@dataclass
class PageScreenshot:
    page_name: str
    page_index: int
    image_bytes: bytes


async def _wait_for_render(page: Page):
    """Wait for Power BI visuals to fully render."""
    try:
        await page.wait_for_selector(
            "visual-container, .visualContainer, .visual, explore-canvas",
            timeout=30000,
        )
    except Exception:
        logger.warning("Visual container not found, using timer fallback")
    await asyncio.sleep(RENDER_WAIT_MS / 1000)


async def capture_report_pages(
    url: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> list[PageScreenshot]:
    """
    Open a Power BI public embed URL with Playwright and screenshot every page.

    Args:
        url: Public embed URL (may include URL-based filters)
        on_progress: Optional callback(page_index, total, page_name)

    Returns:
        List of PageScreenshot ordered by page index
    """
    screenshots: list[PageScreenshot] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # Retina quality screenshots
        )
        page = await context.new_page()

        logger.info("Loading Power BI report: %s", url[:120])
        await page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
        await _wait_for_render(page)

        # Hide Power BI toolbar/header for clean screenshots
        await page.evaluate("""
            () => {
                const selectors = ['.logoBarWrapper', '.reportHeader', '.actionBarWrapper'];
                selectors.forEach(s => {
                    const el = document.querySelector(s);
                    if (el) el.style.display = 'none';
                });
            }
        """)

        # Detect page navigation tabs — try multiple Power BI selector patterns
        PAGE_TAB_SELECTORS = [
            ".navigation .pages-container button",
            ".pageNavigation button",
            ".pages .pageTab",
            "[aria-label='Page navigation'] button",
            "button[role='tab']",
            ".tab-row button",
            ".pages-container li",
        ]
        page_tabs = []
        for selector in PAGE_TAB_SELECTORS:
            found = await page.query_selector_all(selector)
            if found:
                page_tabs = found
                logger.info("Found %d page tabs via selector: %s", len(found), selector)
                break

        if not page_tabs:
            # Single-page report
            logger.info("Single-page report detected")
            if on_progress:
                on_progress(0, 1, "Página 1")
            img = await page.screenshot(type="png", full_page=False)
            screenshots.append(PageScreenshot(page_name="Página 1", page_index=0, image_bytes=img))
        else:
            total = len(page_tabs)
            logger.info("Multi-page report: %d pages", total)

            for i, tab in enumerate(page_tabs):
                tab_text = (await tab.inner_text()).strip()
                page_name = tab_text or f"Página {i + 1}"

                if on_progress:
                    on_progress(i, total, page_name)

                logger.info("Capturing %d/%d: %s", i + 1, total, page_name)
                await tab.click()
                await asyncio.sleep(3)
                await _wait_for_render(page)

                # Re-hide header (may reappear after navigation)
                await page.evaluate("""
                    () => {
                        const selectors = ['.logoBarWrapper', '.reportHeader', '.actionBarWrapper'];
                        selectors.forEach(s => {
                            const el = document.querySelector(s);
                            if (el) el.style.display = 'none';
                        });
                    }
                """)

                img = await page.screenshot(type="png", full_page=False)
                screenshots.append(PageScreenshot(page_name=page_name, page_index=i, image_bytes=img))

        await browser.close()

    logger.info("Captured %d page screenshots", len(screenshots))
    return screenshots
