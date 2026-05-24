"""
NexusSearchClient — Cliente async para comunicarse con la API del backend.
Realiza búsquedas semánticas contra el endpoint /api/v1/search del servidor FastAPI.
"""
import httpx
from typing import Optional


class NexusSearchClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url.rstrip("/")

    async def search(
        self,
        query: str,
        engine: Optional[str] = None,
        top_k: int = 5,
        variant: str = "B"
    ) -> list[dict]:
        """
        Busca prompts semánticamente en el backend Nexus.
        Retorna una lista de dicts con: prompt_text, engine, score, source, author.
        """
        params = {
            "q": query,
            "top_k": top_k,
            "variant": variant,
        }
        if engine:
            params["engine"] = engine

        # base_url ya incluye /api/v1, el endpoint es /search → /api/v1/search
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "prompt_text": item.get("prompt", item.get("prompt_text", "")),
                "engine":      item.get("engine", "Unknown"),
                "score":       round(item.get("score", 0.0), 3),
                "source":      item.get("platform", "nexus"),
                "author":      item.get("author", "unknown"),
            })

        return results

    async def health(self) -> bool:
        """Verifica que el backend esté disponible."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # El health endpoint está en la raíz /health/live
                resp = await client.get(f"{self.base_url}/health/live")
                if resp.status_code == 200:
                    return True
                # Fallback a raíz
                resp2 = await client.get(f"{self.base_url.replace('/api/v1', '')}/")
                return resp2.status_code == 200
        except Exception:
            return False

    async def get_prompts_by_category(
        self,
        categoria_id: int,
        subcategoria_id: str,
        top_k: int = 50
    ) -> list[dict]:
        """
        Obtiene prompts filtrados por categoría y subcategoría.
        """
        params = {
            "categoria_id": categoria_id,
            "subcategoria_id": subcategoria_id,
            "top_k": top_k
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/prompts/category", params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append({
                "prompt_text": item.get("prompt_text", ""),
                "engine":      item.get("engine", "Unknown"),
                "score":       float(item.get("score", 0.0)),
                "votos":       int(item.get("votos", 0)),
                "source":      item.get("source", "nexus"),
                "hash_id":     item.get("hash_id", ""),
            })

        return results

    async def vote_prompt(self, hash_id: str) -> dict:
        """
        Registra un voto útil para un prompt en base a su hash_id.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{self.base_url}/prompts/{hash_id}/vote")
            resp.raise_for_status()
            return resp.json()
