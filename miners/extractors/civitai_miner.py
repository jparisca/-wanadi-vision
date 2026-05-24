"""
Civitai Miner — Extrae prompts directamente de la API pública de Civitai.
Civitai es el repositorio de modelos de Stable Diffusion más grande del mundo
y expone una API REST pública con prompts reales y métricas de engagement.
Esta es la fuente de mayor calidad para prompts de Stable Diffusion / SDXL / Flux.
"""
import hashlib
from datetime import datetime
from typing import AsyncGenerator

import httpx

from miners.core.base_miner import BaseMiner
from miners.core.models import ScrapedPrompt

CIVITAI_API_BASE = "https://civitai.com/api/v1"

# Tipos de imágenes a buscar (las que tienen prompts visibles)
CIVITAI_SORT_OPTIONS = ["Most Reactions", "Most Comments", "Newest"]


class CivitaiMiner(BaseMiner):
    """
    Miner para Civitai.com — la mejor fuente de prompts reales con alta calidad.
    Usa la API pública de Civitai sin necesidad de autenticación.
    """

    @property
    def source_name(self) -> str:
        return "civitai"

    async def fetch_latest_prompts(self, limit: int = 50) -> AsyncGenerator[ScrapedPrompt, None]:
        seen_ids: set[str] = set()
        per_page = min(limit, 20)  # Civitai limita a 200 por request

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            for sort in CIVITAI_SORT_OPTIONS:
                url = f"{CIVITAI_API_BASE}/images"
                params = {
                    "limit": per_page,
                    "sort": sort,
                    "nsfw": "None",  # Solo SFW
                    "period": "Day",
                }

                try:
                    resp = await client.get(url, params=params, timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("items", [])

                    print(f"[CivitaiMiner] ✅ {len(items)} imágenes obtenidas (sort: {sort})")

                    for item in items:
                        meta = item.get("meta") or {}
                        prompt_text = meta.get("prompt", "").strip()

                        if not prompt_text or len(prompt_text) < 20:
                            continue

                        item_id = str(item.get("id", ""))
                        uid = hashlib.sha256(f"civitai_{item_id}".encode()).hexdigest()

                        if uid in seen_ids:
                            continue
                        seen_ids.add(uid)

                        # Detectar motor desde los metadatos
                        model_info = item.get("baseModel", "").lower()
                        if "xl" in model_info or "sdxl" in model_info:
                            engine = "stable_diffusion_xl"
                        elif "flux" in model_info:
                            engine = "flux"
                        elif "sd" in model_info or "stable" in model_info:
                            engine = "stable_diffusion"
                        else:
                            engine = "stable_diffusion"

                        # Engagement: suma de stats disponibles
                        stats = item.get("stats", {})
                        engagement = (
                            stats.get("heartCount", 0)
                            + stats.get("likeCount", 0)
                            + stats.get("commentCount", 0) * 3  # comentarios valen más
                        )

                        yield ScrapedPrompt(
                            id=uid,
                            source=self.source_name,
                            raw_text=prompt_text,
                            engine=engine,
                            image_url=item.get("url"),
                            author=item.get("username"),
                            engagement_score=engagement,
                            scraped_at=datetime.utcnow(),
                        )

                except Exception as e:
                    print(f"[CivitaiMiner] Error fetching (sort={sort}): {e}")
                    continue
