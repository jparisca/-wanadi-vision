import math
from typing import List, Dict, Any

def compute_log_engagement(raw_score: float) -> float:
    """
    Aplica atenuación logarítmica para mitigar sesgo de posts extremadamente virales.
    """
    return math.log(max(raw_score, 0.0) + 1.0)

def normalize_log_engagements(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normaliza el engagement logarítmico sobre una lista de candidatos en base al máximo valor detectado.
    """
    log_engs = [compute_log_engagement(c["raw_engagement"]) for c in candidates]
    max_log_eng = max(log_engs) if log_engs else 0.0
    
    for c, log_eng in zip(candidates, log_engs):
        c["normalized_engagement"] = (log_eng / max_log_eng) if max_log_eng > 0.0 else 0.0
        
    return candidates
