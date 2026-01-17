"""Tweet scoring for reply potential."""

import logging

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.config import ReplyConfig
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)


class TweetScorer:
    """Scores tweets for reply potential."""

    # Scoring weights
    WEIGHT_TOPIC = 0.35
    WEIGHT_ENGAGEMENT = 0.30
    WEIGHT_FOLLOWERS = 0.20
    WEIGHT_RECENCY = 0.15

    def __init__(
        self,
        config: ReplyConfig,
        boost_topics: list[str],
        state: StateManager,
    ):
        """Initialize the tweet scorer.

        Args:
            config: Reply configuration
            boost_topics: List of topics to boost (from scoring config)
            state: StateManager for checking replied tweets
        """
        self.config = config
        # Use reply-specific topics if set, otherwise use boost_topics
        self.topics = config.topics if config.topics else boost_topics
        self.state = state

    def score(self, tweet: ScrapedTweet) -> float:
        """Score a tweet from 0.0 to 1.0.

        Args:
            tweet: The scraped tweet to score

        Returns:
            Score between 0.0 and 1.0
        """
        # Immediate disqualifications
        if self.state.is_tweet_replied(tweet.tweet_id):
            logger.debug(f"Tweet {tweet.tweet_id} already replied to")
            return 0.0

        if tweet.is_retweet:
            logger.debug(f"Tweet {tweet.tweet_id} is a retweet, skipping")
            return 0.0

        if not tweet.content.strip():
            logger.debug(f"Tweet {tweet.tweet_id} has no content")
            return 0.0

        # Calculate individual scores
        scores = []

        # Topic relevance (0-1)
        topic_score = self._score_topic_relevance(tweet.content)
        scores.append(("topic", topic_score, self.WEIGHT_TOPIC))

        # Engagement score (0-1) - normalize to reasonable range
        engagement = tweet.likes + tweet.retweets * 2 + tweet.replies * 3
        engagement_score = min(1.0, engagement / 100)  # 100+ = max score
        scores.append(("engagement", engagement_score, self.WEIGHT_ENGAGEMENT))

        # Author follower range (0-1)
        if tweet.author_followers is not None:
            follower_score = self._score_follower_range(tweet.author_followers)
        else:
            follower_score = 0.5  # Unknown = neutral
        scores.append(("followers", follower_score, self.WEIGHT_FOLLOWERS))

        # Recency bonus (0-1)
        # For now, all scraped tweets are considered "recent"
        recency_score = 0.8
        scores.append(("recency", recency_score, self.WEIGHT_RECENCY))

        # Calculate weighted average
        total = sum(score * weight for _, score, weight in scores)

        logger.debug(
            f"Tweet {tweet.tweet_id[:8]}... scores: "
            f"topic={topic_score:.2f}, engagement={engagement_score:.2f}, "
            f"followers={follower_score:.2f}, recency={recency_score:.2f}, "
            f"total={total:.2f}"
        )

        return total

    def _score_topic_relevance(self, content: str) -> float:
        """Score topic relevance via keyword matching.

        Args:
            content: Tweet content

        Returns:
            Score between 0.0 and 1.0
        """
        if not self.topics:
            return 0.5  # No topics configured = neutral

        content_lower = content.lower()
        matches = sum(1 for topic in self.topics if topic.lower() in content_lower)

        if matches == 0:
            return 0.1  # Baseline for being on timeline

        # More matches = higher score
        return min(1.0, 0.3 + matches * 0.2)

    def _score_follower_range(self, followers: int) -> float:
        """Score based on follower count - sweet spot is 5K-100K.

        Args:
            followers: Author's follower count

        Returns:
            Score between 0.0 and 1.0
        """
        if followers < self.config.target_min_followers:
            return 0.3  # Too small - less visibility

        if followers > self.config.target_max_followers:
            return 0.4  # Too big - harder to get noticed

        # Sweet spot: 5K-100K followers
        if 5000 <= followers <= 100000:
            return 1.0

        # Good range but not optimal
        return 0.7

    def filter_and_rank(
        self,
        tweets: list[ScrapedTweet],
    ) -> list[tuple[ScrapedTweet, float]]:
        """Filter and rank tweets by score.

        Args:
            tweets: List of scraped tweets

        Returns:
            List of (tweet, score) tuples, sorted by score descending
        """
        scored = [(t, self.score(t)) for t in tweets]

        # Filter by threshold
        filtered = [(t, s) for t, s in scored if s >= self.config.score_threshold]

        # Sort by score descending
        ranked = sorted(filtered, key=lambda x: x[1], reverse=True)

        logger.info(
            f"Scored {len(tweets)} tweets, {len(filtered)} passed threshold "
            f"({self.config.score_threshold})"
        )

        return ranked
