"""
News Models
Dataclasses for news collection and analysis
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class NewsSentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class NewsSource(str, Enum):
    CRYPTOPANIC = "cryptopanic"
    COINDESK = "coindesk"
    COINGECKO = "coingecko"
    COINTELEGRAPH = "cointelegraph"
    THEBLOCK = "theblock"


@dataclass
class NewsArticle:
    """Single news article"""
    id: str
    source: NewsSource
    title: str
    summary: str
    url: str
    published_at: datetime
    sentiment: Optional[NewsSentiment] = None
    relevance_score: float = 0.0
    currencies: List[str] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class DailyNewsDigest:
    """Daily aggregated news digest"""
    date: str
    total_articles: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_articles: List[NewsArticle]
    trending_currencies: List[str]
    market_sentiment: NewsSentiment
