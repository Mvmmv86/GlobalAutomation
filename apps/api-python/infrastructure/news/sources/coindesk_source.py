"""
CoinDesk News Source
Fetches news from CoinDesk RSS feed
"""

from datetime import datetime
from typing import List
from time import mktime

import structlog
import httpx

from .base_source import BaseNewsSource
from ..models import NewsArticle, NewsSource

logger = structlog.get_logger(__name__)


class CoinDeskSource(BaseNewsSource):
    """CoinDesk RSS feed news source"""

    RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss"  # Sem barra no final
    # Alternative: JSON API
    API_URL = "https://www.coindesk.com/pf/api/v3/content/fetch/story-feed"

    @property
    def name(self) -> str:
        return "CoinDesk"

    async def fetch_news(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch news from CoinDesk"""
        try:
            # Try RSS first (no API key needed)
            return await self._fetch_rss(limit)
        except Exception as e:
            logger.error(f"CoinDesk fetch failed: {e}")
            return []

    async def _fetch_rss(self, limit: int) -> List[NewsArticle]:
        """Fetch and parse RSS feed"""
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed, skipping CoinDesk RSS")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(self.RSS_URL)
                response.raise_for_status()
                content = response.text

            feed = feedparser.parse(content)
            return self._parse_feed(feed, limit)

        except Exception as e:
            logger.error(f"CoinDesk RSS fetch failed: {e}")
            return []

    def _parse_feed(self, feed, limit: int) -> List[NewsArticle]:
        """Parse RSS feed entries"""
        articles = []

        for entry in feed.entries[:limit]:
            try:
                # Parse published date
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
                else:
                    published_at = datetime.utcnow()

                # Extract summary
                summary = ""
                if hasattr(entry, 'summary'):
                    summary = entry.summary[:500]  # Limit length
                elif hasattr(entry, 'description'):
                    summary = entry.description[:500]

                articles.append(NewsArticle(
                    id=entry.get("id", entry.link),
                    source=NewsSource.COINDESK,
                    title=entry.title,
                    summary=summary,
                    url=entry.link,
                    published_at=published_at,
                    currencies=["BTC", "ETH"],  # Default major cryptos
                    raw_data=dict(entry)
                ))

            except Exception as e:
                logger.debug(f"Failed to parse CoinDesk entry: {e}")
                continue

        return articles
