from functools import lru_cache
import numpy as np
from search.model_registry import get_model

MODEL_NAME = "all-MiniLM-L6-v2"

@lru_cache(maxsize=512)
def _embed_text_to_bytes(text: str) -> bytes:
    """
    Inferencia de embedding de texto con SentenceTransformer.
    Retorna bytes compactos para evitar sobrecarga de memoria de tuplas.
    """
    model = get_model(MODEL_NAME)
    vector = model.encode(text)
    
    # Normalización L2 activa del vector de consulta
    norm = np.linalg.norm(vector)
    if norm > 0.0:
        vector = vector / norm
        
    return vector.astype(np.float32).tobytes()

def get_cached_embedding(text: str) -> np.ndarray:
    """
    Retorna el embedding normalizado L2 como un array de NumPy (float32).
    Normaliza la entrada para evitar fallos de caché y usa almacenamiento eficiente de bytes.
    """
    normalized_text = text.strip().lower()
    bytes_data = _embed_text_to_bytes(normalized_text)
    return np.frombuffer(bytes_data, dtype=np.float32).copy()

