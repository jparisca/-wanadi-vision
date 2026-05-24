import sys
import os
import time
from typing import List, Dict, Any, Optional

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search.retrievers.semantic_retriever import SemanticRetriever
from search.rankers.hybrid_ranker import HybridRanker
from search.query_cache import _embed_text_to_bytes
from search.analytics_worker import AnalyticsWorker

# Configuración global de ranking y retrieval
RANKER_CONFIG = {
    "semantic_weight": 0.85,
    "engagement_weight": 0.15,
    "threshold": 0.45,
    "top_candidates": 30
}

# Inicializar componentes modulares persistentes (Singleton)
_retriever = None
_ranker = None

def get_search_components():
    global _retriever, _ranker
    if _retriever is None:
        _retriever = SemanticRetriever()
    if _ranker is None:
        _ranker = HybridRanker(
            semantic_weight=RANKER_CONFIG["semantic_weight"],
            engagement_weight=RANKER_CONFIG["engagement_weight"]
        )
    return _retriever, _ranker

# Inicializar worker de telemetría por lotes (Singleton — hilo persistente compartido)
_analytics_worker = AnalyticsWorker()

def search_hybrid(query_text: str, engine_filter: Optional[str] = None, top_k: int = 5, variant: str = "B") -> List[Dict[str, Any]]:
    """
    Función de búsqueda híbrida orquestada por las capas de Retrieval y Ranking.
    Mide telemetría de latencias y registra hits de caché en base a las estadísticas del registry.
    """
    start_time = time.perf_counter()
    
    # Obtener hits de la caché LRU antes de ejecutar
    hits_before = _embed_text_to_bytes.cache_info().hits
    
    try:
        retriever, ranker = get_search_components()
        
        # 1. Recuperar candidatos semánticos iniciales usando FAISS HNSW (Etapa 1)
        candidates = retriever.retrieve(
            query_text=query_text,
            top_candidates=RANKER_CONFIG["top_candidates"],
            threshold=RANKER_CONFIG["threshold"]
        )
        
        # 2. Refinar y ordenar con el ranking híbrido logarítmico (Etapa 2)
        # Añadida variante A/B para evaluación del ranker
        results = ranker.rank(
            candidates=candidates,
            engine_filter=engine_filter,
            top_k=top_k,
            variant=variant
        )
        
        # Telemetría final
        latency_ms = (time.perf_counter() - start_time) * 1000
        hits_after = _embed_text_to_bytes.cache_info().hits
        cache_hit = 1 if hits_after > hits_before else 0
        
        top_result_hash = results[0]["hash_id"] if results else None
        
        # Encolar analíticas de forma segura y ultra-rápida (lotes en background)
        _analytics_worker.log_event(query_text, latency_ms, cache_hit, top_result_hash)
        
        return results
        
    except Exception as e:
        print(f"❌ Error en búsqueda semántica híbrida: {e}")
        return []



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 search/semantic_search.py \"tu consulta aquí\" [Midjourney/Flux/Stable Diffusion]")
        sys.exit(1)
        
    query = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else None
    
    results = search_hybrid(query, engine)
    
    print("\n" + "="*75)
    print(f"🎯 RESULTADOS DE BÚSQUEDA HÍBRIDA MULTI-CAPA PARA: \"{query}\"")
    if engine:
        print(f"   [Filtro Motor: {engine}]")
    print(f"   [Filtro: Score Semántico >= {RANKER_CONFIG['threshold']}]")
    print("="*75)
    
    if not results:
        print("   No se encontraron resultados que superen el umbral semántico.")
    else:
        for idx, res in enumerate(results, 1):
            print(f"{idx}) SCORE FINAL: {res['hybrid_score']:.4f}")
            print(f"   📊 DETALLE: Semántico: {res['semantic_score']:.4f} | Engagement: {res['normalized_engagement']:.4f} (Max Raw Source: {res['raw_engagement']:.0f})")
            print(f"   ⚙️  MOTOR: {res['engine']}")
            if res['parameters'] and res['parameters'].get('normalized'):
                print(f"   ⚙️  PARÁMETROS: {res['parameters']['normalized']}")
            print(f"   PROMPT:")
            print(f"   {res['prompt_text']}")
            print(f"   [Hash: {res['hash_id'][:8]}...]")
            print("─" * 75)
