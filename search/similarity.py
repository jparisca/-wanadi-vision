import numpy as np

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcula la similitud del coseno entre dos vectores de una dimensión.
    """
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot_product / (norm_a * norm_b))
