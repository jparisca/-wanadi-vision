from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class ScrapedPrompt(BaseModel):
    id: str = Field(..., description="Unique hash or ID of the post")
    source: str = Field(..., description="E.g., reddit, threads, twitter, civitai")
    raw_text: str = Field(..., description="The actual prompt text")
    engine: str = Field(default="unknown", description="E.g., midjourney, stable_diffusion")
    image_url: Optional[str] = Field(default=None, description="URL of the generated image if available")
    author: Optional[str] = Field(default=None, description="Author username")
    engagement_score: int = Field(default=0, description="Likes/Upvotes")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
