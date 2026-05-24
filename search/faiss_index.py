import numpy as np
import faiss
from sqlalchemy.orm import selectinload
from database.db_utils import get_session
from database.schema import Prompt, PromptEmbedding, PromptVersion

MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384

def build_faiss_index():
    """
    Construye un índice FAISS IndexFlatIP (Inner Product) en base a los embeddings normalizados L2.
    Retorna la tupla (index, mappings_list) para consultas instantáneas.
    """
    session = get_session()
    try:
        # Cargar prompts y sus embeddings de forma eager
        results = (
            session.query(Prompt, PromptEmbedding)
            .options(
                selectinload(Prompt.versions).selectinload(PromptVersion.sources)
            )
            .join(PromptEmbedding)
            .filter(
                Prompt.embedding_status == "completed",
                PromptEmbedding.model_name == MODEL_NAME
            )
            .all()
        )
        
        if not results:
            return None, []
            
        vectors = []
        mappings = []
        
        for prompt, prompt_emb in results:
            vector = np.frombuffer(prompt_emb.vector, dtype=np.float32)
            # Asegurar dimensiones correctas
            if len(vector) == VECTOR_DIM:
                vectors.append(vector)
                mappings.append({
                    "prompt_id": prompt.id,
                    "prompt": prompt
                })
                
        if not vectors:
            return None, []
            
        # Convertir a matriz NumPy float32
        matrix = np.vstack(vectors).astype(np.float32)
        
        # Como los vectores están normalizados L2, IndexFlatIP calcula el coseno exacto (Producto Punto)
        index = faiss.IndexFlatIP(VECTOR_DIM)
        index.add(matrix)
        
        return index, mappings
        
    except Exception as e:
        print(f"❌ Error construyendo el índice FAISS: {e}")
        return None, []
    finally:
        session.close()
