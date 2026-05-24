from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from .models import ScrapedPrompt

class BaseMiner(ABC):
    """
    Abstract base class for all Data Miners.
    Defines the contract for scraping and extracting prompts from social networks.
    """
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the data source (e.g., 'reddit', 'threads')"""
        pass

    @abstractmethod
    async def fetch_latest_prompts(self, limit: int = 100) -> AsyncGenerator[ScrapedPrompt, None]:
        """
        Asynchronously yields parsed ScrapedPrompt objects.
        """
        pass
