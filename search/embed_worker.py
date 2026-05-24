import sys
import os
import numpy as np

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Prompt, PromptEmbedding
from database.db_utils import get_session
from search.model_registry import get_model

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64

def embed_pending_prompts():
    session = get_session()
    try:
        # 1. Buscar prompts pendientes
        pending_prompts = session.query(Prompt).filter_by(embedding_status="pending").all()
        
        if not pending_prompts:
            print("✅ No hay prompts pendientes por vectorizar.")
            return
            
        print(f"🔄 Encontrados {len(pending_prompts)} prompts pendientes.")
        print(f"📥 Cargando modelo local '{MODEL_NAME}'...")
        
        # 2. Cargar modelo de embeddings (se descargará de HuggingFace en la primera corrida)
        model = get_model(MODEL_NAME)
        
        # 3. Procesar en batches
        for i in range(0, len(pending_prompts), BATCH_SIZE):
            batch = pending_prompts[i:i + BATCH_SIZE]
            texts = [p.canonical_text for p in batch]
            
            print(f"🧠 Vectorizando batch {i//BATCH_SIZE + 1} ({len(batch)} prompts)...")
            embeddings = model.encode(texts)
            
            for prompt, embedding in zip(batch, embeddings):
                # Evitar embeddings duplicados para el mismo prompt y modelo
                existing = session.query(PromptEmbedding).filter_by(
                    prompt_id=prompt.id,
                    model_name=MODEL_NAME
                ).first()
                
                if existing:
                    print(f"⏩ Embedding ya existe para prompt ID {prompt.id}. Omitiendo creación.")
                    prompt.embedding_status = "completed"
                    continue

                # Normalización L2 del embedding para habilitar Producto Punto rápido en cosine (Cambio 3)
                norm = np.linalg.norm(embedding)
                if norm > 0.0:
                    embedding = embedding / norm

                # Serializar el vector a bytes compactos float32
                vector_bytes = embedding.astype(np.float32).tobytes()
                vector_dim = int(len(embedding))
                
                # Crear registro de embedding
                prompt_embedding = PromptEmbedding(
                    prompt_id=prompt.id,
                    model_name=MODEL_NAME,
                    vector=vector_bytes,
                    vector_dim=vector_dim
                )
                session.add(prompt_embedding)
                
                # Cambiar estado del prompt canónico
                prompt.embedding_status = "completed"
                
            session.commit()
            print(f"💾 Batch procesado y guardado en base de datos.")
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error en el embed worker: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    embed_pending_prompts()
