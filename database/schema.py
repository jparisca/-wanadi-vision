from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Float, BLOB, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Prompt(Base):
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True)
    hash_id = Column(String(64), unique=True, index=True) # SHA-256 de normalized_text
    canonical_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    embedding_status = Column(String(20), default="pending") # pending, completed, failed
    categoria_id = Column(Integer, nullable=True)
    subcategoria_id = Column(String(100), nullable=True)
    votos = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    versions = relationship("PromptVersion", back_populates="prompt")
    embeddings = relationship("PromptEmbedding", back_populates="prompt")

class PromptEmbedding(Base):
    __tablename__ = "prompt_embeddings"
    
    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    model_name = Column(String(100), nullable=False) # e.g. "all-MiniLM-L6-v2"
    vector = Column(BLOB, nullable=False) # Array de NumPy serializado
    vector_dim = Column(Integer, nullable=False) # Dimensión del vector (ej. 384)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    prompt = relationship("Prompt", back_populates="embeddings")
    
    __table_args__ = (
        UniqueConstraint(
            "prompt_id",
            "model_name",
            name="uq_prompt_model"
        ),
    )

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    
    id = Column(Integer, primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    
    engine = Column(String(50), index=True) # Midjourney, Flux, Stable Diffusion
    parameters = Column(JSON, default=dict) # {"raw": {...}, "normalized": {...}, "confidence": 1.0}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    prompt = relationship("Prompt", back_populates="versions")
    sources = relationship("PromptSource", back_populates="version")

class PromptSource(Base):
    __tablename__ = "prompt_sources"
    
    id = Column(Integer, primary_key=True)
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"))
    
    platform = Column(String(50)) # Reddit, X, Threads
    author = Column(String(100))
    url = Column(String(255))
    engagement_score = Column(Float, default=0.0)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    version = relationship("PromptVersion", back_populates="sources")

class SearchEvent(Base):
    __tablename__ = "search_events"
    
    id = Column(Integer, primary_key=True)
    query = Column(String(255), nullable=False)
    latency = Column(Float, nullable=False) # latency in ms
    cache_hit = Column(Integer, default=0) # 0 = False, 1 = True (SQLite friendly integer/boolean)
    top_result_hash = Column(String(64), nullable=True) # top result hash_id if found
    clicked = Column(Integer, default=0) # SQLite friendly boolean
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

