import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ajuste de path para importaciones correctas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routes import search, health, admin

# Configuración premium de metadatos de Swagger/OpenAPI
app = FastAPI(
    title="🌌 Nexus Prompt API",
    description="""
    El motor de recuperación semántica híbrida más avanzado para prompts de imágenes de Inteligencia Artificial.
    
    ### Características:
    * **Similitud Semántica Local**: Vectorización rápida con `all-MiniLM-L6-v2`.
    * **Ranking Híbrido Ponderado**: Equilibrio de similitud semántica (85%) y engagement viral normalizado logarítmicamente (15%).
    * **Filtros Estrictos**: Exclusión de ruido conceptual (umbral >= 0.45) y filtro por motores de IA.
    * **Explainability Total**: Desglose transparente de scores.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware de CORS para permitir conexiones externas/frontend futuro
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
allow_creds = "*" not in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(search.router, prefix="/api/v1", tags=["Retrieval Engine"])
app.include_router(health.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin Panel"])

@app.get("/", tags=["Root"])
def root():
    return {
        "service": "Nexus Prompt API",
        "version": "1.0.0",
        "health_live": "/api/v1/health/live",
        "health_ready": "/api/v1/health/ready",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Inicialización local en puerto 8000
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=True)
