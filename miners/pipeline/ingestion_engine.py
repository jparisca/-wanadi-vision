import sys
import os
import asyncio

# Configurar path para poder importar módulos de prompt_nexus
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import List
from miners.core.base_miner import BaseMiner
from miners.extractors.civitai_miner import CivitaiMiner
from miners.extractors.reddit_miner import RedditMiner
from miners.extractors.threads_miner import ThreadsMiner

from refinery.cleaner import PromptRefinery
from database.db_utils import save_prompt_to_db
from search.embed_worker import embed_pending_prompts
from search.index_manager import IndexManager

# ─── Clasificación automática por palabras clave ──────────────────────────────
KEYWORD_MAP = {
    "animacion_series": ["pixar", "simpsons", "ghibli", "anime", "cartoon", "disney", "studio ghibli"],
    "videojuegos":      ["minecraft", "zelda", "pokemon", "pixel art", "8-bit", "fortnite", "cuphead"],
    "marketing":        ["product photography", "advertisement", "commercial", "brand", "packaging", "lifestyle"],
    "comida":           ["food photography", "restaurant", "meal", "dish", "coffee", "cake", "drink", "cuisine"],
    "ecommerce":        ["product shot", "white background", "isolated product", "studio shot", "mockup"],
    "moda":             ["fashion", "model", "runway", "clothing", "outfit", "editorial fashion", "lookbook"],
    "arquitectura":     ["architecture", "interior design", "building", "room", "house", "apartment"],
    "naturaleza":       ["landscape", "forest", "ocean", "mountain", "sunset", "nature", "wilderness"],
    "deportes":         ["football", "running", "athlete", "sports", "soccer", "basketball", "surfing"],
    "ciencia_tec":      ["laboratory", "science", "technology", "robot", "neural network", "spacecraft"],
    "estilo_artistico": ["oil painting", "watercolor", "acuarela", "cyberpunk", "vaporwave", "steampunk", "pixel art", "manga"],
    "horror":           ["horror", "scary", "gothic", "lovecraftian", "dark", "creepy", "monster"],
}

def clasificar_prompt(prompt_text: str) -> tuple[str, str]:
    """Devuelve (categoria_slug, subcategoria_slug) o ('tematica', 'general')"""
    text_lower = prompt_text.lower()
    for categoria, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return categoria, kw.replace(" ", "_")
    return "tematica", "general"

class IngestionEngine:
    """
    Orchestrates the data extraction from multiple Miners,
    cleans the prompts via Refinery, saves to DB, computes embeddings,
    and updates the FAISS index autonomously.
    """
    
    def __init__(self, miners: List[BaseMiner]):
        self.miners = miners
        self.refinery = PromptRefinery()

    async def ingest_all(self, limit_per_source: int = 50):
        print("🚀 [IngestionEngine] Iniciando recolección de mineros...")
        
        total_inserted = 0
        
        for miner in self.miners:
            print(f"\n[IngestionEngine] ⛏️ Ejecutando minero: {miner.source_name.upper()}")
            count = 0
            
            async for prompt in miner.fetch_latest_prompts(limit=limit_per_source):
                try:
                    # 1. Refinar y estructurar el texto
                    refined = self.refinery.process(prompt.raw_text)
                    
                    # 2. Guardar en SQLite (embedding_status="pending")
                    save_prompt_to_db(
                        refinery_result=refined,
                        platform=prompt.source,
                        url=prompt.image_url or f"https://{prompt.source}.com/p/{prompt.id}",
                        author=prompt.author or "unknown",
                        engagement_score=float(prompt.engagement_score)
                    )
                    count += 1
                except Exception as e:
                    print(f"❌ [IngestionEngine] Error guardando prompt de {prompt.source}: {e}")
                    
            print(f"[IngestionEngine] ✅ Extraídos {count} prompts de {miner.source_name.upper()}")
            total_inserted += count
            
        if total_inserted > 0:
            print("\n🧠 [IngestionEngine] Computando Embeddings para nuevos prompts...")
            embed_pending_prompts()
            
            print("\n⚡ [IngestionEngine] Refrescando índice FAISS en memoria...")
            manager = IndexManager()
            manager.refresh()
            print("🎉 [IngestionEngine] Pipeline ETL completado con éxito.")
        else:
            print("\n💤 [IngestionEngine] No se encontraron nuevos prompts para procesar.")

if __name__ == "__main__":
    active_miners = [
        CivitaiMiner(),          # ✅ API pública — más confiable
        RedditMiner(),           # ✅ OAuth + fallback RSS
        ThreadsMiner(),          # 🔄 Playwright / sessionid
    ]
    
    engine = IngestionEngine(miners=active_miners)
    asyncio.run(engine.ingest_all(limit_per_source=50))

