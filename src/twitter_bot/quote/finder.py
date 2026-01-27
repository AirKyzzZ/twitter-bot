"""Find trending tweets in Maxime's topics for quote tweeting.

DATA-DRIVEN: Quote tweets get 3.7% engagement vs 1.8% for standard tweets.
Strategy: Find high-engagement tweets in AI, SSI, Dev, Startups topics.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import tweepy

if TYPE_CHECKING:
    from twitter_bot.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TrendingTweet:
    """A trending tweet candidate for quote tweeting."""
    
    tweet_id: str
    author_handle: str
    author_name: str
    author_followers: int
    content: str
    likes: int
    retweets: int
    replies: int
    created_at: datetime
    url: str
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score (likes worth more than RTs)."""
        # Twitter algo: Like: +30, RT: +20, Reply: +1
        return (self.likes * 30 + self.retweets * 20 + self.replies) / max(self.author_followers, 1) * 1000

    @property
    def is_recent(self) -> bool:
        """Check if tweet is recent (< 6h old for max visibility)."""
        age = datetime.utcnow() - self.created_at
        return age < timedelta(hours=6)


# Keywords to search for trending content in Maxime's domains
TOPIC_QUERIES = {
    "ai": [
        "AI agent",
        "LLM production",
        "Claude API",
        "GPT-4 coding",
        "AI automation",
        "vibe coding",
        "AI developer tools",
    ],
    "ssi": [
        "self-sovereign identity",
        "verifiable credentials",
        "DIDComm",
        "decentralized identity",
        "digital identity wallet",
    ],
    "dev": [
        "Next.js 15",
        "TypeScript tips",
        "React server components",
        "Rust web",
        "developer experience",
        "shipping fast",
    ],
    "startups": [
        "indie hacker",
        "bootstrapped startup",
        "solo founder",
        "side project launched",
        "MVP feedback",
        "building in public",
    ],
}


class TrendingTweetFinder:
    """Find trending tweets in Maxime's topics using Twitter API v2."""

    def __init__(self, bearer_token: str):
        """Initialize with Twitter API bearer token."""
        self.client = tweepy.Client(bearer_token=bearer_token)
        
    @classmethod
    def from_settings(cls, settings: "Settings") -> "TrendingTweetFinder":
        """Create finder from settings."""
        return cls(settings.twitter.bearer_token)

    def search_topic(
        self,
        topic: str,
        max_results: int = 10,
        min_likes: int = 50,
        min_followers: int = 1000,
    ) -> list[TrendingTweet]:
        """Search for trending tweets in a specific topic.
        
        Args:
            topic: Topic key (ai, ssi, dev, startups)
            max_results: Maximum tweets to return
            min_likes: Minimum likes threshold
            min_followers: Minimum author followers
            
        Returns:
            List of TrendingTweet objects sorted by engagement
        """
        queries = TOPIC_QUERIES.get(topic, [])
        if not queries:
            logger.warning(f"Unknown topic: {topic}")
            return []
        
        results = []
        
        for query in queries[:3]:  # Limit to 3 queries per topic to conserve API
            try:
                # Search recent tweets with engagement
                response = self.client.search_recent_tweets(
                    query=f"{query} -is:retweet lang:en",
                    max_results=min(max_results, 100),
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    user_fields=["public_metrics", "username", "name"],
                    expansions=["author_id"],
                )
                
                if not response.data:
                    continue
                
                # Build user lookup
                users = {u.id: u for u in (response.includes.get("users", []) or [])}
                
                for tweet in response.data:
                    author = users.get(tweet.author_id)
                    if not author:
                        continue
                    
                    metrics = tweet.public_metrics or {}
                    author_metrics = author.public_metrics or {}
                    
                    likes = metrics.get("like_count", 0)
                    followers = author_metrics.get("followers_count", 0)
                    
                    # Apply filters
                    if likes < min_likes or followers < min_followers:
                        continue
                    
                    trending = TrendingTweet(
                        tweet_id=tweet.id,
                        author_handle=author.username,
                        author_name=author.name,
                        author_followers=followers,
                        content=tweet.text,
                        likes=likes,
                        retweets=metrics.get("retweet_count", 0),
                        replies=metrics.get("reply_count", 0),
                        created_at=tweet.created_at,
                        url=f"https://twitter.com/{author.username}/status/{tweet.id}",
                    )
                    results.append(trending)
                    
            except tweepy.TweepyException as e:
                logger.warning(f"Search failed for '{query}': {e}")
                continue
        
        # Sort by engagement and return top results
        results.sort(key=lambda t: t.engagement_score, reverse=True)
        return results[:max_results]

    def find_quotable_tweets(
        self,
        topics: list[str] | None = None,
        max_per_topic: int = 5,
        total_max: int = 10,
    ) -> list[TrendingTweet]:
        """Find the best tweets to quote across all topics.
        
        Args:
            topics: List of topics to search (default: all)
            max_per_topic: Max tweets per topic
            total_max: Total max tweets to return
            
        Returns:
            List of best TrendingTweet candidates
        """
        if topics is None:
            topics = list(TOPIC_QUERIES.keys())
        
        all_tweets = []
        
        for topic in topics:
            tweets = self.search_topic(topic, max_results=max_per_topic)
            all_tweets.extend(tweets)
            logger.info(f"Found {len(tweets)} quotable tweets for topic '{topic}'")
        
        # Deduplicate by tweet_id
        seen = set()
        unique = []
        for tweet in all_tweets:
            if tweet.tweet_id not in seen:
                seen.add(tweet.tweet_id)
                unique.append(tweet)
        
        # Sort by engagement and recency (prefer recent + high engagement)
        unique.sort(
            key=lambda t: (t.is_recent, t.engagement_score),
            reverse=True,
        )
        
        return unique[:total_max]
