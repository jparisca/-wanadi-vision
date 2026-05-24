import sys
import os
import json
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Prompt, PromptEmbedding
from database.db_utils import DATABASE_URL
from search.model_registry import get_model

MODEL_NAME = "all-MiniLM-L6-v2"

def update_golden_embeddings():
    print("🔮 [Embedding Updater] Iniciando vectorización real de prompts de oro...")
    
    # 1. Leer golden_queries.json
    queries_path = "evaluation/golden_queries.json"
    if not os.path.exists(queries_path):
        print(f"❌ '{queries_path}' no existe.")
        return
        
    with open(queries_path, "r") as f:
        queries = json.load(f)
        
    # Obtener todos los IDs esperados únicos
    expected_ids = set()
    for q in queries:
        expected_ids.update(q["expected_ids"])
        
    print(f"🎯 Encontrados {len(expected_ids)} prompts de oro únicos a vectorizar de verdad.")
    
    # 2. Conectar a BD
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        model = get_model(MODEL_NAME)
        count = 0
        
        for pid in sorted(expected_ids):
            # Obtener el prompt de la BD
            prompt = session.query(Prompt).filter_by(id=pid).first()
            if not prompt:
                print(f"⚠️  Prompt ID {pid} no encontrado en base de datos.")
                continue
                
            # Generar vector real
            text = prompt.canonical_text
            vector = model.encode(text)
            
            # Normalización L2 activa
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            # Buscar o crear el PromptEmbedding correspondientes
            emb = session.query(PromptEmbedding).filter_by(prompt_id=pid, model_name=MODEL_NAME).first()
            if not emb:
                emb = PromptEmbedding(
                    prompt_id=pid,
                    model_name=MODEL_NAME,
                    vector=vector.astype(np.float32).tobytes(),
                    vector_dim=384
                )
                session.add(emb)
            else:
                emb.vector = vector.astype(np.float32).tobytes()
                
            count += 1
            if count % 20 == 0:
                print(f"   ✍️  Vectorizados {count} de {len(expected_ids)} prompts...")
                
        session.commit()
        print(f"✨ [Embedding Updater] Completado. {count} prompts actualizados con embeddings reales de all-MiniLM-L6-v2!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ [Embedding Updater] Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    update_golden_embeddings()
