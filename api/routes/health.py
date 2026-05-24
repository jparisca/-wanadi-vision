from fastapi import APIRouter, HTTPException
from search.index_manager import IndexManager
from database.db_utils import get_session
from database.schema import Prompt

router = APIRouter()

@router.get("/health/live", tags=["Health Check"])
def liveness_probe():
    """
    Indicates whether the application process is running and able to accept requests.
    """
    return {"status": "alive"}

@router.get("/health/ready", tags=["Health Check"])
def readiness_probe():
    """
    Indicates whether the application is fully initialized, database is reachable, and the search index is loaded.
    """
    health_status = {
        "ready": False,
        "index_loaded": False,
        "db_ok": False,
        "embedding_model_loaded": True # SentenceTransformer is loaded lazily and thread-safe
    }
    
    # Check Database
    session = get_session()
    try:
        session.query(Prompt.id).limit(1).scalar()
        health_status["db_ok"] = True
    except Exception as e:
        health_status["db_ok"] = False
    finally:
        session.close()
        
    # Check Index
    manager = IndexManager()
    stats = manager.stats()
    if stats.get("active_vectors", 0) > 0 and stats.get("index_file_exists", False):
        health_status["index_loaded"] = True
        
    if health_status["db_ok"] and health_status["index_loaded"]:
        health_status["ready"] = True
        return health_status
    else:
        # 503 Service Unavailable if not fully ready
        raise HTTPException(status_code=503, detail=health_status)
