from typing import List, Dict, Any, Optional
from search.scorers.engagement import normalize_log_engagements

class HybridRanker:
    def __init__(self, semantic_weight: float = 0.85, engagement_weight: float = 0.15):
        self.semantic_weight = semantic_weight
        self.engagement_weight = engagement_weight
        
    def rank(self, candidates: List[Dict[str, Any]], engine_filter: Optional[str] = None, top_k: int = 5, variant: str = "B") -> List[Dict[str, Any]]:
        """
        Ordena y filtra el Candidate Set aplicando ranking híbrido o de similitud según la variante A/B.
        - Variante A: Similitud semántica pura (100% semántico).
        - Variante B: Ranking híbrido optimizado (85% semántico + 15% engagement logarítmico).
        """
        if not candidates:
            return []
            
        # 1. Expandir a combinaciones Prompt + Versión ganadora filtrando por motor
        expanded_candidates = []
        for cand in candidates:
            dto = cand["prompt_dto"]
            semantic_score = cand["semantic_score"]
            
            for version in dto["versions"]:
                if engine_filter and version["engine"].lower() != engine_filter.lower():
                    continue
                    
                # Engagement máximo por versión
                scores = [float(s["engagement_score"]) for s in version["sources"] if s.get("engagement_score") is not None]
                max_engagement = max(scores, default=0.0)
                
                expanded_candidates.append({
                    "prompt_id": dto["prompt_id"],
                    "version_id": version["id"],
                    "semantic_score": semantic_score,
                    "raw_engagement": max_engagement,
                    "engine": version["engine"],
                    "parameters": version["parameters"],
                    "prompt_text": dto["prompt_text"],
                    "hash_id": dto["hash_id"]
                })
                
        if not expanded_candidates:
            return []
            
        # 2. Normalizar engagement logarítmicamente
        expanded_candidates = normalize_log_engagements(expanded_candidates)
        
        # 3. Calcular Score Híbrido Final según Variante
        import math
        for c in expanded_candidates:
            if variant.upper() == "A":
                # Variante A: Puro Semántico
                c["hybrid_score"] = float(c["semantic_score"])
            else:
                # Variante B: Híbrido Multiplicativo Elasticado (Semántico * (1 + beta * log(1+E)))
                # Evita que la popularidad rescate resultados semánticamente irrelevantes, controlando el crecimiento asintótico.
                norm_eng = float(c.get("normalized_engagement", 0.0))
                c["hybrid_score"] = float(c["semantic_score"]) * (1.0 + self.engagement_weight * math.log1p(norm_eng))
            
        # 4. Ordenar y recortar al top_k
        expanded_candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return expanded_candidates[:top_k]


