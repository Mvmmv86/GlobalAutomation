"""
CoinTelegraph News Source
Fetches news from CoinTelegraph RSS feed
"""

from datetime import datetime
from typing import List
from time import mktime

import structlog
import httpx

from .base_source import BaseNewsSource
from ..models import NewsArticle, NewsSource, NewsSentiment

logger = structlog.get_logger(__name__)


class CoinTelegraphSource(BaseNewsSource):
    """CoinTelegraph RSS feed news source"""

    RSS_URL = "https://cointelegraph.com/rss"

    @property
    def name(self) -> str:
        return "CoinTelegraph"

    async def fetch_news(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch news from CoinTelegraph RSS"""
        try:
            return await self._fetch_rss(limit)
        except Exception as e:
            logger.error(f"CoinTelegraph fetch failed: {e}")
            return []

    async def _fetch_rss(self, limit: int) -> List[NewsArticle]:
        """Fetch and parse RSS feed"""
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser not installed, skipping CoinTelegraph RSS")
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.RSS_URL, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
                })
                response.raise_for_status()
                content = response.text

            feed = feedparser.parse(content)
            return self._parse_feed(feed, limit)

        except Exception as e:
            logger.error(f"CoinTelegraph RSS fetch failed: {e}")
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
                    # Remove HTML tags from summary
                    import re
                    summary = re.sub(r'<[^>]+>', '', entry.summary)[:500]
                elif hasattr(entry, 'description'):
                    import re
                    summary = re.sub(r'<[^>]+>', '', entry.description)[:500]

                # Extract categories/tags for currency detection
                currencies = self._extract_currencies(entry)

                # Analyze sentiment from title
                sentiment = self._analyze_title_sentiment(entry.title)

                articles.append(NewsArticle(
                    id=entry.get("id", entry.link),
                    source=NewsSource.COINTELEGRAPH,
                    title=entry.title,
                    summary=summary,
                    url=entry.link,
                    published_at=published_at,
                    sentiment=sentiment,
                    currencies=currencies,
                    raw_data=dict(entry)
                ))

            except Exception as e:
                logger.debug(f"Failed to parse CoinTelegraph entry: {e}")
                continue

        return articles

    def _extract_currencies(self, entry) -> List[str]:
        """Extract cryptocurrency mentions from entry"""
        currencies = []

        # Common crypto symbols to look for
        crypto_symbols = ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "DOT", "MATIC", "AVAX"]

        text = f"{entry.title} {getattr(entry, 'summary', '')}".upper()

        for symbol in crypto_symbols:
            if symbol in text or f"${symbol}" in text:
                currencies.append(symbol)

        # Also check for full names
        if "BITCOIN" in text:
            currencies.append("BTC")
        if "ETHEREUM" in text:
            currencies.append("ETH")
        if "SOLANA" in text:
            currencies.append("SOL")

        return list(set(currencies)) if currencies else ["BTC", "ETH"]

    def _analyze_title_sentiment(self, title: str) -> NewsSentiment:
        """Simple sentiment analysis based on keywords"""
        title_lower = title.lower()

        bullish_words = ["surge", "soar", "rally", "gain", "rise", "bull", "high", "record",
                        "breakthrough", "adoption", "approval", "partnership", "launch"]
        bearish_words = ["crash", "drop", "fall", "plunge", "bear", "low", "decline",
                        "hack", "scam", "fraud", "ban", "regulation", "lawsuit", "sec"]

        bullish_count = sum(1 for word in bullish_words if word in title_lower)
        bearish_count = sum(1 for word in bearish_words if word in title_lower)

        if bullish_count > bearish_count:
            return NewsSentiment.BULLISH
        elif bearish_count > bullish_count:
            return NewsSentiment.BEARISH
        return NewsSentiment.NEUTRAL
