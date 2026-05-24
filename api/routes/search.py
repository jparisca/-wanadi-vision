from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import numpy as np
from api.schemas.search import SearchResponse
from api.services.search_service import SearchService
from database.db_utils import get_session
from database.schema import SearchEvent, Prompt, PromptVersion
from search.index_manager import IndexManager
from search.analytics_worker import AnalyticsWorker

router = APIRouter()

@router.get("/search", response_model=SearchResponse)
def get_search_results(
    q: str = Query(..., min_length=2, description="Texto a buscar semánticamente"),
    engine: Optional[str] = Query(None, description="Filtro opcional por motor de generación (Midjourney, Flux, Stable Diffusion)"),
    top_k: int = Query(5, ge=1, le=50, description="Número máximo de resultados a retornar"),
    variant: str = Query("B", pattern="^(A|B|a|b)$", description="Variante de ranking: A (puro semántico), B (híbrido con engagement)")
):
    """
    Endpoint principal para realizar búsquedas semánticas híbridas con explainability y filtros de motor.
    """
    try:
        results = SearchService.execute_search(
            query=q,
            engine=engine,
            top_k=top_k,
            variant=variant
        )
        return SearchResponse(
            query=q,
            engine_filter=engine,
            limit=top_k,
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el servidor de búsqueda: {str(e)}")


@router.get("/metrics")
def get_operational_metrics():
    """
    Expone métricas operacionales del motor de búsqueda (Latencia P50/P95, Cache Hit Rate, Index Stats y Queue Metrics) desde memoria rápida.
    """
    try:
        manager = IndexManager()
        stats = manager.stats()
        
        worker = AnalyticsWorker()
        worker_stats = worker.stats()
        
        return {
            "search_latency_p50_ms": worker_stats.get("p50_latency_ms", 0.0),
            "search_latency_p95_ms": worker_stats.get("p95_latency_ms", 0.0),
            "cache_hit_rate": worker_stats.get("cache_hit_rate", 0.0),
            "index_size": stats.get("active_vectors", 0),
            "mappings_count": stats.get("mappings_count", 0),
            "state_hash": stats.get("state_hash", ""),
            "last_refreshed": stats.get("last_refreshed"),
            "index_rebuild_total": stats.get("index_rebuild_total", 0),
            "last_rebuild_timestamp": stats.get("last_rebuild_timestamp"),
            "snapshot_load_failures": stats.get("snapshot_load_failures", 0),
            "using_ann": stats.get("using_ann", "HNSWFlat"),
            "queue_depth": worker_stats.get("queue_depth", 0),
            "queue_fill_ratio": worker_stats.get("queue_fill_ratio", 0.0),
            "total_events": worker_stats.get("total_events", 0),
            "dropped_events": worker_stats.get("dropped_events", 0),
            "drop_rate": worker_stats.get("drop_rate", 0.0),
            "worker_flush_latency_ms": worker_stats.get("worker_flush_latency_ms", 0.0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")


@router.get("/prompts/category")
def get_prompts_by_category(
    categoria_id: int = Query(..., description="ID de la categoría"),
    subcategoria_id: str = Query(..., description="Slug de la subcategoría"),
    top_k: int = Query(50, ge=1, le=100)
):
    """
    Retorna prompts pertenecientes a una categoría y subcategoría específica ordenados por votos de mayor a menor.
    """
    session = get_session()
    try:
        results = (
            session.query(Prompt, PromptVersion)
            .join(PromptVersion)
            .filter(
                Prompt.categoria_id == categoria_id,
                Prompt.subcategoria_id == subcategoria_id
            )
            .order_by(Prompt.votos.desc(), Prompt.id.desc())
            .limit(top_k)
            .all()
        )
        
        formatted = []
        for prompt, version in results:
            source_name = "nexus"
            if version.sources:
                source_name = version.sources[0].platform or "nexus"
                
            formatted.append({
                "hash_id": prompt.hash_id,
                "prompt_text": prompt.canonical_text,
                "engine": version.engine,
                "votos": prompt.votos or 0,
                "score": float(prompt.votos or 0),
                "source": source_name,
            })
        return {"results": formatted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.post("/prompts/{hash_id}/vote")
def vote_prompt(hash_id: str):
    """
    Incrementa en +1 el contador de votos de un prompt por su hash_id.
    """
    session = get_session()
    try:
        prompt = session.query(Prompt).filter_by(hash_id=hash_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt no encontrado")
        prompt.votos = (prompt.votos or 0) + 1
        session.commit()
        return {"status": "success", "hash_id": hash_id, "votos": prompt.votos}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


