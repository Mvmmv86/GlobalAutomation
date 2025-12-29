"""
CryptoPanic News Source
Fetches crypto news from CryptoPanic API
"""

from datetime import datetime
from typing import List
import os

import structlog

from .base_source import BaseNewsSource
from ..models import NewsArticle, NewsSource, NewsSentiment

logger = structlog.get_logger(__name__)


class CryptoPanicSource(BaseNewsSource):
    """CryptoPanic API news source"""

    # API v2 - Developer endpoint (conforme documentação atualizada)
    BASE_URL = "https://cryptopanic.com/api/developer/v2/posts/"

    def __init__(self):
        api_key = os.getenv("CRYPTOPANIC_API_KEY")
        super().__init__(api_key=api_key)

    @property
    def name(self) -> str:
        return "CryptoPanic"

    async def fetch_news(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch news from CryptoPanic"""
        if not self.api_key:
            logger.debug("CryptoPanic API key not configured, skipping")
            return []

        params = {
            "auth_token": self.api_key,
            "filter": "important",
            "public": "true"
        }

        try:
            data = await self._make_request(self.BASE_URL, params)
            return self._parse_response(data, limit)
        except Exception as e:
            logger.error(f"CryptoPanic fetch failed: {e}")
            return []

    def _parse_response(self, data: dict, limit: int) -> List[NewsArticle]:
        """Parse CryptoPanic API response"""
        articles = []

        for item in data.get("results", [])[:limit]:
            # Determine sentiment from votes
            sentiment = None
            if item.get("votes"):
                votes = item["votes"]
                positive = votes.get("positive", 0)
                negative = votes.get("negative", 0)

                if positive > negative:
                    sentiment = NewsSentiment.BULLISH
                elif negative > positive:
                    sentiment = NewsSentiment.BEARISH
                else:
                    sentiment = NewsSentiment.NEUTRAL

            # Parse published date
            try:
                published_at = datetime.fromisoformat(
                    item["published_at"].replace("Z", "+00:00")
                )
            except:
                published_at = datetime.utcnow()

            # Extract currencies mentioned
            currencies = [c["code"] for c in item.get("currencies", [])]

            articles.append(NewsArticle(
                id=str(item["id"]),
                source=NewsSource.CRYPTOPANIC,
                title=item.get("title", ""),
                summary=item.get("title", ""),  # CryptoPanic doesn't provide summary
                url=item.get("url", ""),
                published_at=published_at,
                sentiment=sentiment,
                currencies=currencies,
                raw_data=item
            ))

        return articles
