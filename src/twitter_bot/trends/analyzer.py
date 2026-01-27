"""Analyze trending topics to ride viral waves.

Strategy:
- Check Twitter trends before posting
- Match trends to Maxime's expertise (AI, SSI, Dev, Startups)
- Prioritize content that can ride a trending topic
- Time-sensitive: post within first hour of trend for max visibility
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from twitter_bot.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class Trend:
    """A trending topic or hashtag."""
    
    name: str
    tweet_volume: int | None
    url: str | None
    relevance_score: float = 0.0  # How relevant to Maxime's topics


# Keywords that indicate relevance to Maxime's expertise
EXPERTISE_KEYWORDS = {
    "ai": [
        "ai", "artificial intelligence", "chatgpt", "gpt", "claude",
        "llm", "openai", "anthropic", "gemini", "machine learning",
        "ml", "neural", "deep learning", "copilot", "cursor",
    ],
    "dev": [
        "typescript", "javascript", "react", "nextjs", "nodejs",
        "python", "rust", "developer", "coding", "programming",
        "github", "vscode", "api", "frontend", "backend", "devops",
    ],
    "ssi": [
        "identity", "did", "verifiable", "credential", "ssi",
        "blockchain", "web3", "decentralized", "wallet", "privacy",
    ],
    "startups": [
        "startup", "founder", "indie", "saas", "launch", "product",
        "yc", "funding", "bootstrap", "shipping", "mvp",
    ],
}


class TrendAnalyzer:
    """Analyze trends for content timing optimization."""

    def __init__(self, bearer_token: str | None = None):
        """Initialize trend analyzer.
        
        Args:
            bearer_token: Twitter API bearer token (optional)
        """
        self.bearer_token = bearer_token
        self._cached_trends: list[Trend] = []
        self._cache_time: datetime | None = None

    @classmethod
    def from_settings(cls, settings: "Settings") -> "TrendAnalyzer":
        """Create analyzer from settings."""
        return cls(settings.twitter.bearer_token)

    def _calculate_relevance(self, trend_name: str) -> tuple[float, str]:
        """Calculate how relevant a trend is to Maxime's expertise.
        
        Returns:
            Tuple of (relevance_score, matched_category)
        """
        trend_lower = trend_name.lower()
        
        best_score = 0.0
        best_category = "general"
        
        for category, keywords in EXPERTISE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in trend_lower:
                    # Exact match gets higher score
                    if keyword == trend_lower or f"#{keyword}" == trend_lower:
                        score = 1.0
                    else:
                        score = 0.7
                    
                    if score > best_score:
                        best_score = score
                        best_category = category
        
        return best_score, best_category

    def get_trends(
        self,
        woeid: int = 1,  # 1 = Worldwide, 23424819 = France
        max_age_minutes: int = 30,
    ) -> list[Trend]:
        """Get current Twitter trends.
        
        Args:
            woeid: Where On Earth ID (1=worldwide, 23424819=France)
            max_age_minutes: Max cache age before refresh
            
        Returns:
            List of Trend objects sorted by relevance
        """
        # Check cache
        if self._cached_trends and self._cache_time:
            age = (datetime.utcnow() - self._cache_time).total_seconds() / 60
            if age < max_age_minutes:
                return self._cached_trends
        
        # Fetch fresh trends
        trends = self._fetch_trends(woeid)
        
        # Calculate relevance and sort
        for trend in trends:
            score, _ = self._calculate_relevance(trend.name)
            trend.relevance_score = score
        
        # Sort by relevance first, then by volume
        trends.sort(
            key=lambda t: (t.relevance_score, t.tweet_volume or 0),
            reverse=True,
        )
        
        # Cache results
        self._cached_trends = trends
        self._cache_time = datetime.utcnow()
        
        return trends

    def _fetch_trends(self, woeid: int) -> list[Trend]:
        """Fetch trends from Twitter API.
        
        Falls back to mock data if API not available.
        """
        if not self.bearer_token:
            logger.warning("No bearer token, using mock trends")
            return self._get_mock_trends()
        
        try:
            import tweepy
            
            client = tweepy.Client(bearer_token=self.bearer_token)
            # Note: Trends endpoint requires elevated access
            # If not available, fall back to mock
            
            # Twitter API v2 doesn't have a direct trends endpoint
            # We'd need v1.1 API which requires different auth
            # For now, use web scraping alternative or mock
            
            logger.info("Using mock trends (API v2 trends not available)")
            return self._get_mock_trends()
            
        except Exception as e:
            logger.warning(f"Trends fetch failed: {e}")
            return self._get_mock_trends()

    def _get_mock_trends(self) -> list[Trend]:
        """Get mock/typical tech trends for testing."""
        # These represent common tech Twitter trends
        mock_trends = [
            Trend(name="AI", tweet_volume=150000, url=None),
            Trend(name="ChatGPT", tweet_volume=80000, url=None),
            Trend(name="TypeScript", tweet_volume=25000, url=None),
            Trend(name="React", tweet_volume=35000, url=None),
            Trend(name="Python", tweet_volume=45000, url=None),
            Trend(name="#buildinpublic", tweet_volume=5000, url=None),
            Trend(name="Vercel", tweet_volume=8000, url=None),
            Trend(name="Next.js", tweet_volume=12000, url=None),
            Trend(name="Rust", tweet_volume=15000, url=None),
            Trend(name="#DevOps", tweet_volume=10000, url=None),
        ]
        return mock_trends

    def get_relevant_trends(
        self,
        min_relevance: float = 0.5,
        limit: int = 5,
    ) -> list[Trend]:
        """Get only trends relevant to Maxime's expertise.
        
        Args:
            min_relevance: Minimum relevance score (0-1)
            limit: Maximum number of trends to return
            
        Returns:
            List of relevant Trend objects
        """
        all_trends = self.get_trends()
        relevant = [t for t in all_trends if t.relevance_score >= min_relevance]
        return relevant[:limit]

    def suggest_topic_boost(
        self,
        base_topics: list[str],
    ) -> list[str]:
        """Suggest which topics to prioritize based on current trends.
        
        Args:
            base_topics: List of available topics to post about
            
        Returns:
            Reordered list with trending topics first
        """
        trends = self.get_trends()
        trend_names_lower = {t.name.lower().strip("#") for t in trends[:20]}
        
        # Score each topic by trend overlap
        scored = []
        for topic in base_topics:
            topic_lower = topic.lower()
            
            # Check if topic matches any trend
            score = 0
            for trend_name in trend_names_lower:
                if trend_name in topic_lower or topic_lower in trend_name:
                    score += 1
                    break
            
            scored.append((topic, score))
        
        # Sort by score (trending first) but keep some randomness
        import random
        
        trending = [t for t, s in scored if s > 0]
        regular = [t for t, s in scored if s == 0]
        
        random.shuffle(trending)
        random.shuffle(regular)
        
        return trending + regular

    def get_trend_context(self, topic: str) -> str | None:
        """Get context about a trending topic for content generation.
        
        Args:
            topic: Topic to get context for
            
        Returns:
            Context string or None if no relevant trend
        """
        trends = self.get_trends()
        
        for trend in trends:
            trend_lower = trend.name.lower().strip("#")
            if trend_lower in topic.lower() or topic.lower() in trend_lower:
                volume = f" ({trend.tweet_volume:,} tweets)" if trend.tweet_volume else ""
                return f"Currently trending: {trend.name}{volume}"
        
        return None
