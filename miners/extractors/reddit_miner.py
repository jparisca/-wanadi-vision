"""
Reddit Miner — Estrategia Dual:
  1. API OAuth via PRAW (si se configuran credenciales en .env)
  2. Fallback: Pushshift.io (datos históricos, sin auth)
  3. Fallback 2: Reddit RSS (feeds públicos de XML, siempre disponible)

Esto garantiza que nunca nos quedemos sin datos de Reddit aunque bloqueen.
"""
import os
import hashlib
from datetime import datetime
from typing import AsyncGenerator

import httpx

from miners.core.base_miner import BaseMiner
from miners.core.models import ScrapedPrompt

# --- Credenciales opcionales vía variables de entorno ---
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME      = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD      = os.getenv("REDDIT_PASSWORD", "")

SUBREDDITS_AI = [
    "midjourney",
    "StableDiffusion",
    "PromptEngineering",
    "AIArt",
    "dalle2",
]

class RedditMiner(BaseMiner):
    """
    Miner para Reddit con sistema de fallback de 3 capas para evitar bloqueos.
    """

    @property
    def source_name(self) -> str:
        return "reddit"

    def __init__(self, subreddits: list[str] | None = None):
        self.subreddits = subreddits or SUBREDDITS_AI

    # -------------------------------------------------------------------------
    # CAPA 1: OAuth via PRAW token  (requiere credenciales configuradas)
    # -------------------------------------------------------------------------
    async def _get_oauth_token(self, client: httpx.AsyncClient) -> str | None:
        if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD]):
            return None
        try:
            resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
                data={
                    "grant_type": "password",
                    "username": REDDIT_USERNAME,
                    "password": REDDIT_PASSWORD,
                },
                headers={"User-Agent": "PromptNexus/2.0 by /u/prompt_nexus_bot"},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception as e:
            print(f"[RedditMiner] OAuth falló: {e}")
            return None

    async def _fetch_via_oauth(
        self, client: httpx.AsyncClient, token: str, sub: str, limit: int
    ) -> list[dict]:
        url = f"https://oauth.reddit.com/r/{sub}/top.json?limit={limit}&t=day"
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": "PromptNexus/2.0 by /u/prompt_nexus_bot",
        }
        resp = await client.get(url, headers=headers, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])

    # -------------------------------------------------------------------------
    # CAPA 2: RSS XML (100% público, sin auth, sin bloqueos)
    # -------------------------------------------------------------------------
    async def _fetch_via_rss(
        self, client: httpx.AsyncClient, sub: str, limit: int
    ) -> list[dict]:
        """Parsea el RSS de Reddit (JSON embed via .rss?format=json no existe,
        usamos el endpoint .json con headers de browser)."""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.reddit.com/",
        }
        url = f"https://www.reddit.com/r/{sub}/top.json?limit={limit}&t=day"
        resp = await client.get(url, headers=headers, timeout=15.0)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])

    # -------------------------------------------------------------------------
    # EXTRACTOR principal: itera capas de fallback
    # -------------------------------------------------------------------------
    async def fetch_latest_prompts(self, limit: int = 50) -> AsyncGenerator[ScrapedPrompt, None]:
        async with httpx.AsyncClient(follow_redirects=True) as client:

            # Intentar obtener token OAuth
            token = await self._get_oauth_token(client)

            for sub in self.subreddits:
                children: list[dict] = []

                # Capa 1: OAuth
                if token:
                    try:
                        children = await self._fetch_via_oauth(client, token, sub, limit)
                        print(f"[RedditMiner] ✅ OAuth OK → r/{sub} ({len(children)} posts)")
                    except Exception as e:
                        print(f"[RedditMiner] OAuth falló para r/{sub}: {e}")

                # Capa 2: Browser headers (RSS/JSON fallback)
                if not children:
                    try:
                        children = await self._fetch_via_rss(client, sub, limit)
                        print(f"[RedditMiner] ✅ Fallback RSS OK → r/{sub} ({len(children)} posts)")
                    except Exception as e:
                        print(f"[RedditMiner] Fallback también falló para r/{sub}: {e}")

                for child in children:
                    post = child.get("data", {})
                    title    = post.get("title", "")
                    selftext = post.get("selftext", "")
                    raw_text = f"{title} {selftext}".strip()

                    # Filtro mínimo: al menos 20 chars y no es un [deleted]
                    if len(raw_text) < 20 or "[deleted]" in raw_text:
                        continue

                    post_id = post.get("id", hashlib.sha256(raw_text.encode()).hexdigest()[:8])

                    # Detectar motor por el nombre del subreddit
                    if sub.lower() == "midjourney":
                        engine = "midjourney"
                    elif sub.lower() in ("stablediffusion", "aiaart"):
                        engine = "stable_diffusion"
                    elif "dalle" in sub.lower():
                        engine = "dall_e"
                    else:
                        engine = "unknown"

                    yield ScrapedPrompt(
                        id=hashlib.sha256(f"reddit_{sub}_{post_id}".encode()).hexdigest(),
                        source=self.source_name,
                        raw_text=raw_text,
                        engine=engine,
                        image_url=post.get("url"),
                        author=post.get("author"),
                        engagement_score=post.get("score", 0),
                        scraped_at=datetime.utcnow(),
                    )
