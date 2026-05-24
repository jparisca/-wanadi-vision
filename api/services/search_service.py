import sys
import os

# Ajuste de path para importaciones correctas de modulos vecinos
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from search.semantic_search import search_hybrid

class SearchService:
    @staticmethod
    def execute_search(query: str, engine: str = None, top_k: int = 5, variant: str = "B"):
        """
        Ejecuta la busqueda semantica hibrida con filtros opcionales y variante A/B.
        """
        raw_results = search_hybrid(
            query_text=query,
            engine_filter=engine,
            top_k=top_k,
            variant=variant
        )
        
        # Formatear el payload de salida para que coincida con el schema
        formatted_results = []
        for res in raw_results:
            formatted_results.append({
                "score": float(res["hybrid_score"]),
                "semantic": float(res["semantic_score"]),
                "engagement": float(res["normalized_engagement"]),
                "raw_engagement": float(res["raw_engagement"]),
                "engine": res["engine"],
                "parameters": res["parameters"],
                "prompt": res["prompt_text"],
                "hash_id": res["hash_id"]
            })
            
        return formatted_results

