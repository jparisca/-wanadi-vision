import sys
import os
import random
import hashlib
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Base, Prompt, PromptEmbedding, PromptVersion, PromptSource
from database.db_utils import DATABASE_URL, strict_normalize
from search.model_registry import get_model

GOLDEN_SUBJECTS = [
    "cyberpunk cyborg", "ancient elf warrior", "futuristic neon city", 
    "retro spaceship", "mystical fantasy forest", "steampunk mechanical dragon", 
    "minimalist architecture house", "photorealistic rainy street", 
    "space voyager nebula", "samurai dual katana"
]

# Temas de distractores completamente diferentes para evitar solapamiento semántico (needle in a haystack)
DISTRACTOR_SUBJECTS = [
    "delicious homemade pizza with melted cheese",
    "fluffy yellow duckling swimming in a calm pond",
    "vintage record player spinning a classic vinyl",
    "professional tennis player serving on a clay court",
    "majestic snow-capped mountain range during sunrise",
    "colorful tropical parrot sitting on a jungle branch",
    "modern abstract canvas painting with warm brushstrokes",
    "cozy wooden cabin with a brick fireplace and bookshelf",
    "group of business coworkers discussing in a bright office",
    "ripe red apples resting in a rustic wicker basket",
    "toddler laughing while playing with a blue toy car",
    "historic stone castle overlooking a blue ocean cove",
    "golden desert dunes glowing under a full moon sky",
    "fresh bouquet of pink roses sitting in a glass vase",
    "antique brass pocket watch showing Roman numerals",
    "chef decorating a gourmet chocolate cake in a bakery",
    "graceful ballerina dancing in a sunlit studio room",
    "black cat sleeping soundly on a soft velvet cushion",
    "majestic lion walking through dry savanna grass",
    "modern smartphone resting on a sleek marble table"
]

ADJECTIVES = [
    "hyperrealistic", "unreal engine 5 render", "cinematic lighting", 
    "high detail", "masterpiece style", "detailed oil painting", 
    "volumetric fog", "highly atmospheric", "8k resolution", "sharp focus"
]
PLATFORMS = ["Reddit", "X", "Threads", "Pinterest"]
ENGINES = ["Midjourney", "Flux", "Stable Diffusion"]

def populate_database(num_entries=10000):
    print(f"🚀 [Populator] Iniciando generación de {num_entries} registros con distinción semántica...")
    engine = create_engine(DATABASE_URL)
    
    # Recrear esquema completo
    print("🧹 [Populator] Limpiando tablas de base de datos viejas...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        prompts_to_add = []
        embeddings_to_add = []
        versions_to_add = []
        sources_to_add = []
        
        start_time = datetime.now(timezone.utc)
        
        # 1. Generar 100 Golden Prompts (10 por cada tema de oro)
        # Esto nos da un target controlado para calcular MAP y Recall con precisión matemática
        print("🎯 Generando 100 target prompts de oro...")
        prompt_id_counter = 1
        
        for subj in GOLDEN_SUBJECTS:
            for k in range(10):
                adj1 = random.choice(ADJECTIVES)
                adj2 = random.choice(ADJECTIVES)
                while adj2 == adj1:
                    adj2 = random.choice(ADJECTIVES)
                    
                canonical_text = f"A beautiful representation of a {subj}, {adj1}, {adj2}, high resolution version {k}"
                normalized_text = strict_normalize(canonical_text)
                hash_id = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
                
                prompt = Prompt(
                    id=prompt_id_counter,
                    hash_id=hash_id,
                    canonical_text=canonical_text,
                    normalized_text=normalized_text,
                    embedding_status="completed"
                )
                prompts_to_add.append(prompt)
                prompt_id_counter += 1
                
        # 2. Generar 9,900 Distractores Semánticos sin las palabras clave de oro
        print(f"🌾 Generando {num_entries - 100} distractores semánticos...")
        for i in range(num_entries - 100):
            subj = random.choice(DISTRACTOR_SUBJECTS)
            adj1 = random.choice(ADJECTIVES)
            adj2 = random.choice(ADJECTIVES)
            while adj2 == adj1:
                adj2 = random.choice(ADJECTIVES)
                
            canonical_text = f"{subj}, {adj1}, {adj2}, high detail version {i}"
            normalized_text = strict_normalize(canonical_text)
            hash_id = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
            
            prompt = Prompt(
                id=prompt_id_counter,
                hash_id=hash_id,
                canonical_text=canonical_text,
                normalized_text=normalized_text,
                embedding_status="completed"
            )
            prompts_to_add.append(prompt)
            prompt_id_counter += 1

        # 3. Generar versiones y fuentes para todos los prompts generados
        print("⚙️  Generando versiones y fuentes de engagement...")
        for idx, prompt in enumerate(prompts_to_add):
            num_versions = random.randint(1, 2)
            version_engines = random.sample(ENGINES, num_versions)
            
            for v_idx, engine_name in enumerate(version_engines):
                version_id = idx * 3 + v_idx + 1
                version = PromptVersion(
                    id=version_id,
                    prompt_id=prompt.id,
                    engine=engine_name,
                    parameters={"normalized": f"--aspect_ratio 16:9 --v {v_idx + 5}.0"}
                )
                versions_to_add.append(version)
                
                num_sources = random.randint(1, 2)
                platforms_chosen = random.sample(PLATFORMS, num_sources)
                for s_idx, platform in enumerate(platforms_chosen):
                    # Asignar un engagement score aleatorio
                    source = PromptSource(
                        prompt_version_id=version.id,
                        platform=platform,
                        author=f"artist_synth_{random.randint(100, 999)}",
                        url=f"https://{platform.lower()}.com/p/{prompt.hash_id[:12]}",
                        engagement_score=float(random.randint(50, 2000))
                    )
                    sources_to_add.append(source)
                    
        # 4. Batch Encoding Real usando SentenceTransformer
        print("🧠 [Populator] Cargando SentenceTransformer y generando embeddings reales...")
        model = get_model("all-MiniLM-L6-v2")
        
        texts = [p.canonical_text for p in prompts_to_add]
        
        # Inferencia en lotes
        encoded_vectors = model.encode(texts, batch_size=256, show_progress_bar=True)
        
        print("📏 [Populator] Normalizando y empaquetando vectores...")
        for idx, vector in enumerate(encoded_vectors):
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
                
            emb = PromptEmbedding(
                prompt_id=prompts_to_add[idx].id,
                model_name="all-MiniLM-L6-v2",
                vector=vector.astype(np.float32).tobytes(),
                vector_dim=384
            )
            embeddings_to_add.append(emb)
            
        # 5. Guardado Masivo Eficiente
        print("💾 [Populator] Inyectando registros en base de datos...")
        session.bulk_save_objects(prompts_to_add)
        session.bulk_save_objects(embeddings_to_add)
        session.bulk_save_objects(versions_to_add)
        session.bulk_save_objects(sources_to_add)
        
        print("💾 [Populator] Confirmando transacción SQLite...")
        session.commit()
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        print(f"✨ [Populator] {num_entries} registros reales e informaciones de vectores inyectados con éxito en {elapsed:.2f} segundos!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ [Populator] Error en inyección: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    count = 10000
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    populate_database(count)
