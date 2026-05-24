import sys
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Prompt
from database.db_utils import DATABASE_URL

QUERY_TEMPLATES = [
    {"query": "cyberpunk cyborg", "keyword": "cyberpunk cyborg"},
    {"query": "ancient elf warrior", "keyword": "ancient elf warrior"},
    {"query": "futuristic neon city", "keyword": "futuristic neon city"},
    {"query": "retro spaceship", "keyword": "retro spaceship"},
    {"query": "mystical fantasy forest", "keyword": "mystical fantasy forest"},
    {"query": "steampunk mechanical dragon", "keyword": "steampunk mechanical dragon"},
    {"query": "minimalist architecture house", "keyword": "minimalist architecture house"},
    {"query": "photorealistic rainy street", "keyword": "photorealistic rainy street"},
    {"query": "space voyager nebula", "keyword": "space voyager nebula"},
    {"query": "samurai dual katana", "keyword": "samurai dual katana"}
]

def generate_golden_queries():
    print("🔮 [Golden Generator] Iniciando generación dinámica de Golden Queries...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    golden_list = []
    
    try:
        for item in QUERY_TEMPLATES:
            query_str = item["query"]
            keyword = item["keyword"]
            
            # Buscar prompts en base de datos que contengan la keyword (coincidencias reales)
            prompts = session.query(Prompt).filter(Prompt.canonical_text.like(f"%{keyword}%")).limit(10).all()
            expected_ids = [p.id for p in prompts]
            
            if expected_ids:
                golden_list.append({
                    "query": query_str,
                    "expected_ids": expected_ids
                })
                print(f"   ✅ Agregada query '{query_str}' con {len(expected_ids)} IDs esperados.")
            else:
                print(f"   ⚠️  No se encontraron coincidencias para la keyword '{keyword}'")
                
        # Guardar en disco
        output_path = "evaluation/golden_queries.json"
        with open(output_path, "w") as f:
            json.dump(golden_list, f, indent=2)
            
        print(f"✨ [Golden Generator] Creado '{output_path}' exitosamente con {len(golden_list)} golden queries!")
        
    except Exception as e:
        print(f"❌ [Golden Generator] Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    generate_golden_queries()
