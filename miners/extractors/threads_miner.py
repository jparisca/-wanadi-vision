"""
ThreadsMiner v4 — Playwright headless con sessionid inyectado.
Threads es una SPA React; no hay API REST pública sin auth de sesión atada al UA.

Solución: Playwright abre Chromium con la cookie del usuario inyectada.
El UA de Playwright-Chromium es consistente consigo mismo (no importa el mismatch
de la cookie — Playwright ejecuta el JS completo y Meta no hace UA check en el HTML).

Cuando la cookie no funciona (sesión expirada), scraping anónimo de posts públicos.
"""

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime
from typing import AsyncGenerator
from urllib.parse import unquote

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from miners.core.base_miner import BaseMiner
from miners.core.models import ScrapedPrompt

log = logging.getLogger("ThreadsMiner")

SESSION_ID = unquote(os.getenv("THREADS_SESSION_ID", ""))

SEARCH_QUERIES = [
    "midjourney prompt",
    "stable diffusion prompt",
    "AI art prompt",
    "flux image prompt",
    "dall-e prompt",
    "image generation prompt",
]

_PROMPT_RE = re.compile(
    r"\b(prompt|--ar|--v \d|--style|masterpiece|photorealistic|8k|"
    r"ultra.?detailed|cinematic|hyperrealistic|diffusion|midjourney|"
    r"bokeh|HDR|RAW photo|sharp focus|depth of field|4k|"
    r"digital art|concept art|unreal engine|octane render|flux|dall.?e|"
    r"negative prompt|cfg scale|sampler|steps:|LoRA)\b",
    re.IGNORECASE,
)

# Selectores CSS donde Threads pone el texto de los posts
_POST_SELECTORS = [
    "div[class*='x1lliihq'] span[dir='auto']",
    "span[class*='x193iq5w']",
    "div[data-pressable-container] span",
    "article span",
    "[role='article'] span",
    "div[class*='xdj266r'] span",
    "span[class*='x1s688f']",
]


class ThreadsMiner(BaseMiner):
    """Minero de Threads.com usando Playwright headless con cookie de sesión."""

    def __init__(self, max_per_query: int = 15, headless: bool = True):
        self.max_per_query = max_per_query
        self.headless = headless

    @property
    def source_name(self) -> str:
        return "threads"

    async def fetch_latest_prompts(
        self, limit: int = 100
    ) -> AsyncGenerator[ScrapedPrompt, None]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            log.error("[Threads] playwright no instalado: pip install playwright && playwright install chromium")
            return

        per_query = max(5, limit // len(SEARCH_QUERIES))
        count = 0

        async with async_playwright() as pw:
            try:
                browser = await pw.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
            except Exception as e:
                log.warning(f"[Threads] Chromium no disponible: {e}. Ejecuta: playwright install chromium")
                return

            # Crear contexto con la cookie de sesión inyectada
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )

            # Inyectar cookie de sesión si está disponible
            if SESSION_ID:
                await context.add_cookies([{
                    "name": "sessionid",
                    "value": SESSION_ID,
                    "domain": ".threads.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }])
                log.info("[Threads] Cookie de sesión inyectada en Playwright")

            for query in SEARCH_QUERIES:
                if count >= limit:
                    break
                try:
                    page = await context.new_page()
                    posts = await self._scrape_search_page(page, query, per_query)
                    await page.close()

                    for text in posts:
                        if count >= limit:
                            break
                        yield self._make_prompt(text)
                        count += 1

                    log.info(f"[Threads] '{query}': {len(posts)} prompts encontrados")
                    await asyncio.sleep(3.0)

                except Exception as e:
                    log.warning(f"[Threads] Error en '{query}': {e}")
                    try:
                        await page.close()
                    except Exception:
                        pass

            await browser.close()

        log.info(f"[Threads] Ciclo completo: {count} prompts")

    async def _scrape_search_page(
        self, page, query: str, limit: int
    ) -> list[str]:
        """Navega a la búsqueda de Threads y extrae textos de posts visibles."""
        url = f"https://www.threads.com/search?q={query.replace(' ', '+')}&serp_type=recent"
        results = []

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25_000)

            # Esperar que aparezca algún contenido
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                await asyncio.sleep(4)

            # Scroll para cargar más posts
            for _ in range(4):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1.2)

            # Extraer textos probando cada selector
            for selector in _POST_SELECTORS:
                texts = await page.evaluate(f"""
                    () => {{
                        const els = document.querySelectorAll('{selector}');
                        const seen = new Set();
                        const out = [];
                        for (const el of els) {{
                            const t = (el.innerText || el.textContent || '').trim();
                            if (t.length > 40 && t.length < 3000 && !seen.has(t)) {{
                                seen.add(t);
                                out.push(t);
                            }}
                        }}
                        return out;
                    }}
                """)
                if texts:
                    log.debug(f"[Threads] selector '{selector}': {len(texts)} textos")
                    for t in texts:
                        if self._is_prompt(t) and t not in results:
                            results.append(t)
                    if len(results) >= limit:
                        break

        except Exception as e:
            log.debug(f"[Threads] Error scraping '{query}': {e}")

        return results[:limit]

    def _make_prompt(self, text: str) -> ScrapedPrompt:
        uid = hashlib.sha256(f"threads_{text[:60]}".encode()).hexdigest()
        return ScrapedPrompt(
            id=uid,
            source=self.source_name,
            raw_text=text,
            engine=self._detect_engine(text),
            author="threads_user",
            engagement_score=0,
            scraped_at=datetime.utcnow(),
        )

    def _is_prompt(self, text: str) -> bool:
        return bool(_PROMPT_RE.search(text)) and 30 < len(text) < 3000

    def _detect_engine(self, text: str) -> str:
        t = text.lower()
        if "midjourney" in t or "--ar" in t or "--v " in t:
            return "midjourney"
        if "stable diffusion" in t or "sdxl" in t:
            return "stable_diffusion"
        if "flux" in t:
            return "flux"
        if "dall-e" in t or "dalle" in t:
            return "dall_e"
        return "unknown"
