"""
News Collector Service
Aggregates news from multiple sources and stores daily digests
"""

from datetime import datetime
from typing import List, Optional
from dataclasses import asdict
import json

import structlog

from .models import NewsArticle, DailyNewsDigest, NewsSentiment
from .sources.cryptopanic_source import CryptoPanicSource
from .sources.coindesk_source import CoinDeskSource
from .sources.coingecko_source import CoinGeckoSource
from .sources.cointelegraph_source import CoinTelegraphSource
from .sources.theblock_source import TheBlockSource

logger = structlog.get_logger(__name__)


class NewsCollector:
    """
    Collects and aggregates news from multiple sources.
    Designed to run daily via scheduler.

    Sources:
    - CryptoPanic (API) - Aggregated news with sentiment
    - CoinDesk (RSS) - Quality journalism
    - CoinGecko (API) - Trending coins
    - CoinTelegraph (RSS) - International crypto news
    - TheBlock (RSS) - Institutional/research news
    """

    def __init__(self, db_connection=None):
        self.db = db_connection
        self.sources = [
            CryptoPanicSource(),      # Aggregated with sentiment
            CoinDeskSource(),          # Quality journalism
            CoinGeckoSource(),         # Trending coins
            CoinTelegraphSource(),     # International coverage
            TheBlockSource(),          # Institutional focus
        ]

    async def collect_daily_news(self) -> DailyNewsDigest:
        """
        Collect news from all sources and create daily digest.

        Returns:
            DailyNewsDigest with aggregated news data
        """
        all_articles: List[NewsArticle] = []

        for source in self.sources:
            try:
                articles = await source.fetch_news(limit=20)
                all_articles.extend(articles)
                logger.info(
                    f"Collected {len(articles)} articles from {source.name}",
                    source=source.name,
                    count=len(articles)
                )
            except Exception as e:
                logger.error(f"Error collecting from {source.name}: {e}")

        # Sort by date (most recent first)
        all_articles.sort(key=lambda x: x.published_at, reverse=True)

        # Calculate sentiment distribution
        bullish = sum(1 for a in all_articles if a.sentiment == NewsSentiment.BULLISH)
        bearish = sum(1 for a in all_articles if a.sentiment == NewsSentiment.BEARISH)
        neutral = len(all_articles) - bullish - bearish

        # Determine overall market sentiment
        if bullish > bearish * 1.5:
            market_sentiment = NewsSentiment.BULLISH
        elif bearish > bullish * 1.5:
            market_sentiment = NewsSentiment.BEARISH
        else:
            market_sentiment = NewsSentiment.NEUTRAL

        # Find trending currencies
        currency_counts = {}
        for article in all_articles:
            for currency in article.currencies:
                currency_counts[currency] = currency_counts.get(currency, 0) + 1

        trending = sorted(
            currency_counts.keys(),
            key=lambda x: currency_counts[x],
            reverse=True
        )[:10]

        # Create digest
        digest = DailyNewsDigest(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            total_articles=len(all_articles),
            bullish_count=bullish,
            bearish_count=bearish,
            neutral_count=neutral,
            top_articles=all_articles[:20],  # Top 20 articles
            trending_currencies=trending,
            market_sentiment=market_sentiment
        )

        # Save to database if connection provided
        if self.db:
            await self._save_digest(digest)

        logger.info(
            "Daily news collection complete",
            total_articles=len(all_articles),
            bullish=bullish,
            bearish=bearish,
            sentiment=market_sentiment.value,
            trending=trending[:5]
        )

        return digest

    async def _save_digest(self, digest: DailyNewsDigest):
        """Save digest to database"""
        query = """
            INSERT INTO ai_news_digests (date, data, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (date) DO UPDATE SET
                data = $2,
                updated_at = NOW()
        """

        try:
            # Convert to JSON-serializable format
            data = {
                "total_articles": digest.total_articles,
                "bullish_count": digest.bullish_count,
                "bearish_count": digest.bearish_count,
                "neutral_count": digest.neutral_count,
                "market_sentiment": digest.market_sentiment.value,
                "trending_currencies": digest.trending_currencies,
                "articles": [
                    {
                        "id": a.id,
                        "source": a.source.value,
                        "title": a.title,
                        "summary": a.summary[:200] if a.summary else "",
                        "url": a.url,
                        "sentiment": a.sentiment.value if a.sentiment else None,
                        "currencies": a.currencies,
                        "published_at": a.published_at.isoformat()
                    }
                    for a in digest.top_articles
                ]
            }

            await self.db.execute(query, digest.date, json.dumps(data))
            logger.info(f"Saved news digest for {digest.date}")

        except Exception as e:
            logger.error(f"Error saving news digest: {e}")

    async def get_digest(self, date: Optional[str] = None) -> Optional[DailyNewsDigest]:
        """
        Retrieve a saved digest from database.

        Args:
            date: Date string YYYY-MM-DD (default: today)

        Returns:
            DailyNewsDigest or None if not found
        """
        if not self.db:
            return None

        if not date:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        query = """
            SELECT data FROM ai_news_digests WHERE date = $1
        """

        try:
            result = await self.db.fetchrow(query, date)
            if result:
                data = json.loads(result["data"])
                # Reconstruct DailyNewsDigest from stored data
                return DailyNewsDigest(
                    date=date,
                    total_articles=data["total_articles"],
                    bullish_count=data["bullish_count"],
                    bearish_count=data["bearish_count"],
                    neutral_count=data["neutral_count"],
                    top_articles=[],  # Articles stored separately
                    trending_currencies=data["trending_currencies"],
                    market_sentiment=NewsSentiment(data["market_sentiment"])
                )
        except Exception as e:
            logger.error(f"Error retrieving digest: {e}")

        return None
