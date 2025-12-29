"""
Base News Source
Abstract class for all news sources
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
import structlog

from ..models import NewsArticle

logger = structlog.get_logger(__name__)


class BaseNewsSource(ABC):
    """Abstract base class for news sources"""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    @property
    @abstractmethod
    def name(self) -> str:
        """Source name for identification"""
        pass

    @abstractmethod
    async def fetch_news(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch news articles from this source"""
        pass

    async def _make_request(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """Make HTTP request to source API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
