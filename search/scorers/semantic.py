import numpy as np

def dot_product_similarity(query_vector: np.ndarray, doc_vector: np.ndarray) -> float:
    """
    Similitud por Producto Punto.
    Asume que ambos vectores ya están normalizados L2 (equivalente a Coseno exacto).
    """
    return float(np.dot(query_vector, doc_vector))
