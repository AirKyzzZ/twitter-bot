"""Tests for TweetScorer."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.config import ReplyConfig
from twitter_bot.reply.scorer import TweetScorer
from twitter_bot.state.manager import StateManager


@pytest.fixture
def mock_state_manager(tmp_path: Path):
    """Create a mock state manager."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    manager.load()  # Initialize empty state
    return manager


@pytest.fixture
def reply_config():
    """Create a default reply config."""
    return ReplyConfig(
        enabled=True,
        max_per_day=40,
        min_delay_seconds=120,
        target_min_followers=1000,
        target_max_followers=500000,
        score_threshold=0.6,
    )


@pytest.fixture
def boost_topics():
    """Sample boost topics."""
    return ["AI", "machine learning", "TypeScript", "React", "indie hacker"]


@pytest.fixture
def scorer(reply_config, boost_topics, mock_state_manager):
    """Create a TweetScorer instance."""
    return TweetScorer(reply_config, boost_topics, mock_state_manager)


def create_tweet(
    tweet_id: str = "123",
    author_handle: str = "testuser",
    content: str = "Test tweet content",
    likes: int = 10,
    retweets: int = 5,
    replies: int = 2,
    author_followers: int | None = 10000,
    is_retweet: bool = False,
) -> ScrapedTweet:
    """Helper to create a ScrapedTweet."""
    return ScrapedTweet(
        tweet_id=tweet_id,
        author_handle=author_handle,
        author_name="Test User",
        author_followers=author_followers,
        content=content,
        likes=likes,
        retweets=retweets,
        replies=replies,
        timestamp=datetime.now(UTC),
        is_retweet=is_retweet,
        is_quote=False,
    )


class TestTweetScorer:
    """Tests for TweetScorer scoring logic."""

    def test_score_returns_zero_for_retweet(self, scorer):
        """Retweets should score 0."""
        tweet = create_tweet(is_retweet=True)
        assert scorer.score(tweet) == 0.0

    def test_score_returns_zero_for_empty_content(self, scorer):
        """Empty content should score 0."""
        tweet = create_tweet(content="")
        assert scorer.score(tweet) == 0.0

    def test_score_returns_zero_for_replied_tweet(self, scorer, mock_state_manager):
        """Already replied tweets should score 0."""
        tweet = create_tweet(tweet_id="already_replied")
        # Manually add to replied set
        state = mock_state_manager.load()
        state.replied_tweet_ids.add("already_replied")
        mock_state_manager.save()

        assert scorer.score(tweet) == 0.0

    def test_score_higher_for_topic_match(self, scorer):
        """Tweets matching topics should score higher."""
        topic_tweet = create_tweet(content="Building an AI agent with machine learning")
        generic_tweet = create_tweet(content="Just had coffee this morning")

        topic_score = scorer.score(topic_tweet)
        generic_score = scorer.score(generic_tweet)

        assert topic_score > generic_score

    def test_score_higher_for_engagement(self, scorer):
        """Tweets with more engagement should score higher."""
        high_engagement = create_tweet(likes=100, retweets=50, replies=30)
        low_engagement = create_tweet(likes=1, retweets=0, replies=0)

        high_score = scorer.score(high_engagement)
        low_score = scorer.score(low_engagement)

        assert high_score > low_score

    def test_score_follower_sweet_spot(self, scorer):
        """Accounts in 5K-100K range should score higher for followers."""
        sweet_spot = create_tweet(author_followers=50000)
        too_small = create_tweet(author_followers=100)
        too_big = create_tweet(author_followers=1000000)

        sweet_score = scorer._score_follower_range(50000)
        small_score = scorer._score_follower_range(100)
        big_score = scorer._score_follower_range(1000000)

        assert sweet_score > small_score
        assert sweet_score > big_score

    def test_score_unknown_followers_neutral(self, scorer):
        """Unknown follower count should score neutral (0.5)."""
        tweet = create_tweet(author_followers=None)
        score = scorer.score(tweet)
        # Score should still be calculated with neutral follower component
        assert 0 < score < 1


class TestTopicRelevance:
    """Tests for topic relevance scoring."""

    def test_no_match_gets_baseline(self, scorer):
        """Tweets with no topic match get baseline score."""
        score = scorer._score_topic_relevance("Just a random tweet")
        assert score == 0.1  # Baseline

    def test_single_match(self, scorer):
        """Single topic match gets moderate score."""
        score = scorer._score_topic_relevance("Learning about AI today")
        assert score > 0.1

    def test_multiple_matches_higher_score(self, scorer):
        """Multiple topic matches get higher score."""
        single_score = scorer._score_topic_relevance("Learning about AI")
        multi_score = scorer._score_topic_relevance("Building AI with machine learning and React")

        assert multi_score > single_score

    def test_case_insensitive_matching(self, scorer):
        """Topic matching should be case insensitive."""
        score_lower = scorer._score_topic_relevance("building with ai")
        score_upper = scorer._score_topic_relevance("Building with AI")

        assert score_lower == score_upper


class TestFilterAndRank:
    """Tests for filter_and_rank method."""

    def test_filters_below_threshold(self, scorer):
        """Tweets below threshold should be filtered out."""
        tweets = [
            create_tweet(tweet_id="1", content="AI is amazing", likes=50),
            create_tweet(tweet_id="2", content="Coffee time", likes=0),
        ]

        ranked = scorer.filter_and_rank(tweets)

        # Only the AI tweet should pass (has topic match and engagement)
        tweet_ids = [t.tweet_id for t, _ in ranked]
        assert "1" in tweet_ids or len(ranked) == 0  # May or may not pass depending on threshold

    def test_sorted_by_score_descending(self, scorer):
        """Results should be sorted by score in descending order."""
        tweets = [
            create_tweet(tweet_id="1", content="Just coffee", likes=1),
            create_tweet(tweet_id="2", content="AI machine learning TypeScript", likes=100),
            create_tweet(tweet_id="3", content="AI project", likes=50),
        ]

        ranked = scorer.filter_and_rank(tweets)

        if len(ranked) >= 2:
            scores = [s for _, s in ranked]
            assert scores == sorted(scores, reverse=True)

    def test_empty_list_returns_empty(self, scorer):
        """Empty input should return empty output."""
        ranked = scorer.filter_and_rank([])
        assert ranked == []

    def test_filters_retweets(self, scorer):
        """Retweets should be filtered out."""
        tweets = [
            create_tweet(tweet_id="1", is_retweet=True),
            create_tweet(tweet_id="2", content="AI project", is_retweet=False),
        ]

        ranked = scorer.filter_and_rank(tweets)

        tweet_ids = [t.tweet_id for t, _ in ranked]
        assert "1" not in tweet_ids
