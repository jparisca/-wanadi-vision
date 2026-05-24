from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SearchResultItem(BaseModel):
    score: float
    semantic: float
    engagement: float
    raw_engagement: float
    engine: str
    parameters: Optional[Dict[str, Any]] = None
    prompt: str
    hash_id: str

class SearchResponse(BaseModel):
    query: str
    engine_filter: Optional[str] = None
    limit: int
    results: List[SearchResultItem]
