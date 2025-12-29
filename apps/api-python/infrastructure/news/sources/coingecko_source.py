"""
CoinGecko News Source
Fetches trending coins and news from CoinGecko API
"""

from datetime import datetime
from typing import List

import structlog

from .base_source import BaseNewsSource
from ..models import NewsArticle, NewsSource, NewsSentiment

logger = structlog.get_logger(__name__)


class CoinGeckoSource(BaseNewsSource):
    """CoinGecko API news source - provides trending data"""

    BASE_URL = "https://api.coingecko.com/api/v3"

    @property
    def name(self) -> str:
        return "CoinGecko"

    async def fetch_news(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch trending coins as 'news' items"""
        try:
            trending = await self._fetch_trending()
            return self._convert_to_articles(trending, limit)
        except Exception as e:
            logger.error(f"CoinGecko fetch failed: {e}")
            return []

    async def _fetch_trending(self) -> dict:
        """Fetch trending coins from CoinGecko"""
        url = f"{self.BASE_URL}/search/trending"
        return await self._make_request(url)

    def _convert_to_articles(self, data: dict, limit: int) -> List[NewsArticle]:
        """Convert trending coins to article format"""
        articles = []

        coins = data.get("coins", [])[:limit]

        for idx, coin_data in enumerate(coins):
            coin = coin_data.get("item", {})

            # Create a news-like article for trending coin
            title = f"{coin.get('name', 'Unknown')} ({coin.get('symbol', '').upper()}) is trending"

            # Determine sentiment based on price change
            price_change = coin.get("data", {}).get("price_change_percentage_24h", {})
            btc_change = price_change.get("btc", 0) if isinstance(price_change, dict) else 0

            if btc_change > 5:
                sentiment = NewsSentiment.BULLISH
            elif btc_change < -5:
                sentiment = NewsSentiment.BEARISH
            else:
                sentiment = NewsSentiment.NEUTRAL

            # Build summary
            market_cap_rank = coin.get("market_cap_rank", "N/A")
            summary = f"Trending #{idx + 1} on CoinGecko. Market cap rank: #{market_cap_rank}."

            if coin.get("data", {}).get("price"):
                summary += f" Current price: ${coin['data']['price']:.6f}"

            articles.append(NewsArticle(
                id=f"coingecko_trending_{coin.get('id', idx)}_{datetime.utcnow().strftime('%Y%m%d')}",
                source=NewsSource.COINGECKO,
                title=title,
                summary=summary,
                url=f"https://www.coingecko.com/en/coins/{coin.get('id', '')}",
                published_at=datetime.utcnow(),
                sentiment=sentiment,
                currencies=[coin.get("symbol", "").upper()],
                raw_data=coin_data
            ))

        return articles
