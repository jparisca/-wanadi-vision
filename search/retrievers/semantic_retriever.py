import numpy as np
from typing import List, Dict, Any
from search.query_cache import get_cached_embedding
from search.index_manager import IndexManager

class SemanticRetriever:
    def __init__(self):
        self.manager = IndexManager()
        # Intentar refrescar/construir si está vacío
        self.manager.refresh()
        
    def retrieve(self, query_text: str, top_candidates: int = 30, threshold: float = 0.45) -> List[Dict[str, Any]]:
        """
        Recupera el Candidate Set inicial del índice FAISS HNSW ANN que supera el umbral.
        """
        # Refrescar dinámicamente si hay nuevos registros en BD (Index Lifecycle)
        self.manager.refresh()
        
        index = self.manager.index
        mappings = self.manager.mappings
        
        if index is None or not mappings:
            return []
            
        # 1. Obtener vector de consulta L2 normalizado desde la caché LRU (Optimización de entrada normalizada)
        query_vector = get_cached_embedding(query_text)
        
        # 2. Búsqueda vectorial aproximada real (HNSW Flat)
        query_matrix = query_vector.reshape(1, -1).astype(np.float32)
        
        total_items = index.ntotal
        search_k = min(top_candidates * 2, total_items)
        if search_k <= 0:
            return []
            
        scores, indices = index.search(query_matrix, search_k)
        
        candidates = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(mappings):
                continue
                
            semantic_score = float(score)
            if semantic_score >= threshold:
                dto = mappings[idx]
                candidates.append({
                    "prompt_dto": dto,
                    "semantic_score": semantic_score
                })
                
        return candidates

