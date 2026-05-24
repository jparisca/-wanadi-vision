from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.schema import Prompt, PromptVersion, PromptSource
from datetime import datetime, timezone
import re

DATABASE_URL = "sqlite:///nexus_prompts.db"

def get_session():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def strict_normalize(text: str) -> str:
    """
    Normalización estricta idéntica a la usada en el Refinery para calcular el Hash.
    """
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^\w\s,:-]", "", normalized)
    return normalized.strip()

SLUG_TO_ID = {
    "estilo_artistico": 1,
    "animacion_series": 2,
    "videojuegos": 3,
    "tematica": 4,
    "composicion": 5,
    "color": 6,
    "marketing": 7,
    "comida": 8,
    "ecommerce": 9,
    "moda": 10,
    "arquitectura": 11,
    "naturaleza": 12,
    "ciencia_tec": 13,
    "deportes": 14,
    "dificultad": 15,
}

KEYWORD_MAP = {
    "animacion_series": ["pixar", "simpsons", "ghibli", "anime", "cartoon", "disney", "studio ghibli"],
    "videojuegos":      ["minecraft", "zelda", "pokemon", "pixel art", "8-bit", "fortnite", "cuphead"],
    "marketing":        ["product photography", "advertisement", "commercial", "brand", "packaging", "lifestyle"],
    "comida":           ["food photography", "restaurant", "meal", "dish", "coffee", "cake", "drink", "cuisine"],
    "ecommerce":        ["product shot", "white background", "isolated product", "studio shot", "mockup"],
    "moda":             ["fashion", "model", "runway", "clothing", "outfit", "editorial fashion", "lookbook"],
    "arquitectura":     ["architecture", "interior design", "building", "room", "house", "apartment"],
    "naturaleza":       ["landscape", "forest", "ocean", "mountain", "sunset", "nature", "wilderness"],
    "deportes":         ["football", "running", "athlete", "sports", "soccer", "basketball", "surfing"],
    "ciencia_tec":      ["laboratory", "science", "technology", "robot", "neural network", "spacecraft"],
    "estilo_artistico": ["oil painting", "watercolor", "acuarela", "cyberpunk", "vaporwave", "steampunk", "pixel art", "manga"],
}

def clasificar_prompt(prompt_text: str) -> tuple[int, str]:
    """Devuelve (categoria_id, subcategoria_slug)"""
    text_lower = prompt_text.lower()
    for cat_slug, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return SLUG_TO_ID[cat_slug], kw.replace(" ", "_")
    return SLUG_TO_ID["tematica"], "general"

def save_prompt_to_db(refinery_result, platform, url, author, engagement_score=0.0):
    session = get_session()
    
    try:
        hash_id = refinery_result["hash_id"]
        engine_name = refinery_result["engine"]
        parameters = refinery_result["parameters"]
        clean_text = refinery_result["clean_text"]
        
        # 1. Buscar si el Prompt Canónico ya existe
        prompt = session.query(Prompt).filter_by(hash_id=hash_id).first()
        
        if not prompt:
            # Clasificar automáticamente
            cat_id, sub_slug = clasificar_prompt(clean_text)
            
            # Crear nuevo Prompt Canónico
            prompt = Prompt(
                hash_id=hash_id,
                canonical_text=clean_text,
                normalized_text=strict_normalize(clean_text),
                embedding_status="pending",
                categoria_id=cat_id,
                subcategoria_id=sub_slug,
                votos=0
            )
            session.add(prompt)
            session.flush() # Obtener prompt.id
            print(f"✨ Nuevo Prompt Canónico Creado (ID: {prompt.id})")
        
        # 2. Buscar si la versión (Engine + Params) ya existe para este Prompt
        version = None
        for v in prompt.versions:
            if v.engine == engine_name and v.parameters == parameters:
                version = v
                break
                
        if not version:
            version = PromptVersion(
                prompt_id=prompt.id,
                engine=engine_name,
                parameters=parameters
            )
            session.add(version)
            session.flush() # Obtener version.id
            print(f"⚙️  Nueva Versión de Prompt Creada (ID: {version.id} | {engine_name})")
            
        # 3. Buscar si este Source ya existe para esta versión
        source = session.query(PromptSource).filter_by(
            prompt_version_id=version.id,
            platform=platform,
            url=url
        ).first()
        
        if not source:
            source = PromptSource(
                prompt_version_id=version.id,
                platform=platform,
                author=author,
                url=url,
                engagement_score=engagement_score
            )
            session.add(source)
            session.commit()
            print(f"💾 Nuevo Source guardado (ID: {source.id} | Platform: {platform})")
        else:
            print(f"⏩ Source ya existe para esta versión (ID: {source.id}). Omitiendo.")
            
        return prompt
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error guardando en BD: {e}")
        raise e
    finally:
        session.close()
