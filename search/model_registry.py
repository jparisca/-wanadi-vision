from threading import Lock
from sentence_transformers import SentenceTransformer

# Registro privado en memoria
_models = {}
_lock = Lock()

def get_model(name: str) -> SentenceTransformer:
    """
    Retorna la instancia Singleton del modelo de embeddings de forma segura
    ante entornos multihilo / concurrentes como FastAPI.
    """
    with _lock:
        if name not in _models:
            print(f"📥 [Model Registry] Cargando modelo '{name}' de forma segura (Thread-Safe)...")
            _models[name] = SentenceTransformer(name)
    return _models[name]
