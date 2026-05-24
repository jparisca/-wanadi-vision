"""
X (Twitter) Miner — Estrategia sin API Key:
  Usa Nitter (instancias públicas de Twitter frontend alternativo)
  para extraer prompts de hashtags y cuentas especializadas en IA.
  No requiere credenciales ni API key de Twitter/X.
"""
import hashlib
from datetime import datetime
from typing import AsyncGenerator

import httpx
from miners.core.base_miner import BaseMiner
from miners.core.models import ScrapedPrompt

# Instancias públicas de Nitter (mirrors de Twitter sin auth)
NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.1d4.us",
]

# Hashtags de alto valor para minería de prompts
AI_HASHTAGS = [
    "MidjourneyPrompt",
    "AIArt",
    "StableDiffusion",
    "PromptEngineering",
    "AIImageGeneration",
]

# Cuentas curadas de creadores de prompts premium
CURATED_ACCOUNTS = [
    "midjourney",
    "prompthero",
    "PromptBase",
]


class TwitterMiner(BaseMiner):
    """
    Miner para X/Twitter vía instancias Nitter públicas.
    Extrae tweets de hashtags y cuentas curadas sin necesidad de API key.
    """

    @property
    def source_name(self) -> str:
        return "twitter"

    def __init__(self):
        self.active_instance: str | None = None

    async def _find_working_instance(self, client: httpx.AsyncClient) -> str | None:
        """Prueba las instancias Nitter en orden y retorna la primera que responda."""
        for instance in NITTER_INSTANCES:
            try:
                resp = await client.get(instance, timeout=5.0)
                if resp.status_code == 200:
                    print(f"[TwitterMiner] ✅ Instancia Nitter activa: {instance}")
                    return instance
            except Exception:
                continue
        return None

    def _parse_nitter_json(self, data: dict, instance: str) -> list[ScrapedPrompt]:
        """Parsea la respuesta JSON de Nitter y extrae ScrapedPrompts."""
        prompts = []
        items = data.get("items", [])
        for item in items:
            text = item.get("description", "") or item.get("content", "")
            if not text or len(text) < 20:
                continue

            # Filtrar retweets simples sin texto de prompt
            if text.startswith("RT @"):
                continue

            author  = item.get("author", {})
            link    = item.get("url", "")
            likes   = item.get("attachments", {}).get("likes", 0) if isinstance(item.get("attachments"), dict) else 0

            uid = hashlib.sha256(f"twitter_{link}".encode()).hexdigest()
            prompts.append(ScrapedPrompt(
                id=uid,
                source=self.source_name,
                raw_text=text.strip(),
                engine="unknown",
                image_url=None,
                author=author.get("name") if isinstance(author, dict) else str(author),
                engagement_score=likes,
                scraped_at=datetime.utcnow(),
            ))
        return prompts

    async def _fetch_hashtag(
        self, client: httpx.AsyncClient, instance: str, hashtag: str, limit: int
    ) -> list[ScrapedPrompt]:
        """Extrae tweets de un hashtag vía el RSS/JSON de Nitter."""
        url = f"{instance}/search/rss?q=%23{hashtag}&f=tweets"
        try:
            resp = await client.get(url, timeout=10.0)
            resp.raise_for_status()
            # Nitter RSS es XML — parseamos manualmente los <title> de items
            import re
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)
            links  = re.findall(r"<link>(https://[^\s<]+)</link>", resp.text)

            prompts = []
            for i, (title, link) in enumerate(zip(titles[1:], links)):  # skip channel title
                if len(title) < 20 or title.startswith("RT @"):
                    continue
                uid = hashlib.sha256(f"twitter_ht_{hashtag}_{i}".encode()).hexdigest()
                prompts.append(ScrapedPrompt(
                    id=uid,
                    source=self.source_name,
                    raw_text=title.strip(),
                    engine="unknown",
                    image_url=None,
                    author=f"#{hashtag}",
                    engagement_score=0,
                    scraped_at=datetime.utcnow(),
                ))
                if len(prompts) >= limit:
                    break
            return prompts
        except Exception as e:
            print(f"[TwitterMiner] Error en hashtag #{hashtag}: {e}")
            return []

    async def fetch_latest_prompts(self, limit: int = 50) -> AsyncGenerator[ScrapedPrompt, None]:
        per_tag = max(5, limit // len(AI_HASHTAGS))

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            instance = await self._find_working_instance(client)
            if not instance:
                print("[TwitterMiner] ⚠️  No hay instancias Nitter disponibles. Skipping X.")
                return

            seen_ids: set[str] = set()
            for hashtag in AI_HASHTAGS:
                prompts = await self._fetch_hashtag(client, instance, hashtag, per_tag)
                for p in prompts:
                    if p.id not in seen_ids:
                        seen_ids.add(p.id)
                        yield p
