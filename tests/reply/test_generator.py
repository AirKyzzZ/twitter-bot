"""Tests for ReplyGenerator."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import GenerationResult, LLMProvider
from twitter_bot.reply.generator import (
    REPLY_TYPE_INSTRUCTIONS,
    REPLY_TYPES,
    ReplyGenerator,
)
from twitter_bot.state.manager import StateManager


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "This is a test reply"):
        self.response = response
        self.last_prompt: str | None = None

    def generate(self, prompt: str, max_tokens: int = 500) -> GenerationResult:
        self.last_prompt = prompt
        return GenerationResult(text=self.response, model="mock")

    def generate_multiple(
        self, prompt: str, n: int = 3, max_tokens: int = 500
    ) -> list[GenerationResult]:
        return [self.generate(prompt, max_tokens) for _ in range(n)]


@pytest.fixture
def mock_state_manager(tmp_path: Path):
    """Create a mock state manager."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)
    manager.load()  # Initialize empty state
    return manager


@pytest.fixture
def mock_provider():
    """Create a mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def generator(mock_provider, mock_state_manager):
    """Create a ReplyGenerator instance."""
    voice_profile = "You are Maxime, a 19-year-old builder from Bordeaux."
    return ReplyGenerator(mock_provider, voice_profile, mock_state_manager)


def create_tweet(
    tweet_id: str = "123",
    author_handle: str = "testuser",
    content: str = "Test tweet about building things",
    likes: int = 10,
    retweets: int = 5,
    replies: int = 2,
) -> ScrapedTweet:
    """Helper to create a ScrapedTweet."""
    return ScrapedTweet(
        tweet_id=tweet_id,
        author_handle=author_handle,
        author_name="Test User",
        author_followers=10000,
        content=content,
        likes=likes,
        retweets=retweets,
        replies=replies,
        timestamp=datetime.now(UTC),
        is_retweet=False,
        is_quote=False,
    )


class TestReplyTypes:
    """Tests for reply type constants."""

    def test_all_reply_types_have_instructions(self):
        """All reply types should have corresponding instructions."""
        for reply_type in REPLY_TYPES:
            assert reply_type in REPLY_TYPE_INSTRUCTIONS

    def test_reply_types_are_valid(self):
        """Reply types should match expected values."""
        expected = ["witty", "agree_twist", "hot_take", "one_liner", "flex"]
        assert REPLY_TYPES == expected


class TestReplyGenerator:
    """Tests for ReplyGenerator."""

    def test_generate_reply_returns_tuple(self, generator):
        """generate_reply should return (text, type) tuple."""
        tweet = create_tweet()
        result = generator.generate_reply(tweet)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)  # reply text
        assert isinstance(result[1], str)  # reply type

    def test_generate_reply_type_in_valid_types(self, generator):
        """Reply type should be one of the valid types."""
        tweet = create_tweet()
        _, reply_type = generator.generate_reply(tweet)

        assert reply_type in REPLY_TYPES

    def test_prompt_includes_tweet_content(self, generator, mock_provider):
        """Generated prompt should include the tweet content."""
        tweet = create_tweet(content="This is a unique test content")
        generator.generate_reply(tweet)

        assert "This is a unique test content" in mock_provider.last_prompt

    def test_prompt_includes_author_handle(self, generator, mock_provider):
        """Generated prompt should include the author handle."""
        tweet = create_tweet(author_handle="unique_handle")
        generator.generate_reply(tweet)

        assert "@unique_handle" in mock_provider.last_prompt

    def test_prompt_includes_reply_type_instructions(self, generator, mock_provider):
        """Generated prompt should include type-specific instructions."""
        tweet = create_tweet()
        _, reply_type = generator.generate_reply(tweet)

        assert REPLY_TYPE_INSTRUCTIONS[reply_type] in mock_provider.last_prompt

    def test_prompt_includes_identity(self, generator, mock_provider):
        """Generated prompt should include the identity."""
        tweet = create_tweet()
        generator.generate_reply(tweet)

        assert "maxime" in mock_provider.last_prompt
        assert "bordeaux" in mock_provider.last_prompt


class TestCleanReply:
    """Tests for reply text cleaning."""

    def test_clean_removes_quotes(self, generator):
        """Should remove surrounding quotes."""
        assert generator._clean_reply('"Test reply"') == "Test reply"
        assert generator._clean_reply("'Test reply'") == "Test reply"

    def test_clean_removes_prefix(self, generator):
        """Should remove Reply: prefix."""
        assert generator._clean_reply("Reply: Test reply") == "Test reply"
        assert generator._clean_reply("reply: Test reply") == "Test reply"
        assert generator._clean_reply("Response: Test reply") == "Test reply"

    def test_clean_strips_whitespace(self, generator):
        """Should strip whitespace."""
        assert generator._clean_reply("  Test reply  ") == "Test reply"

    def test_clean_handles_normal_text(self, generator):
        """Should leave normal text unchanged."""
        assert generator._clean_reply("Normal reply text") == "Normal reply text"


class TestReplyLength:
    """Tests for reply length handling."""

    def test_truncates_long_replies(self, generator, mock_state_manager):
        """Replies over 280 chars should be truncated."""
        long_response = "A" * 300  # 300 characters
        provider = MockLLMProvider(response=long_response)
        gen = ReplyGenerator(provider, "voice", mock_state_manager)

        tweet = create_tweet()
        reply, _ = gen.generate_reply(tweet)

        assert len(reply) <= 280

    def test_short_replies_unchanged(self, generator, mock_state_manager):
        """Short replies should not be modified."""
        short_response = "A short reply"
        provider = MockLLMProvider(response=short_response)
        gen = ReplyGenerator(provider, "voice", mock_state_manager)

        tweet = create_tweet()
        reply, _ = gen.generate_reply(tweet)

        assert reply == short_response


class TestReplyTypeRotation:
    """Tests for reply type rotation via state manager."""

    def test_first_reply_uses_witty(self, generator, mock_state_manager):
        """First reply should use 'witty' type."""
        tweet = create_tweet()
        _, reply_type = generator.generate_reply(tweet)

        # First call to get_next_reply_type should return 'witty'
        assert reply_type == "witty"

    def test_rotation_cycles_types(self, mock_state_manager):
        """Reply types should rotate over multiple calls."""
        provider = MockLLMProvider()
        voice_profile = "voice"
        gen = ReplyGenerator(provider, voice_profile, mock_state_manager)

        types_used = set()
        for i in range(10):
            tweet = create_tweet(tweet_id=str(i))
            _, reply_type = gen.generate_reply(tweet)
            types_used.add(reply_type)
            # Record type in state manager to simulate actual usage
            mock_state_manager.load().reply_type_history.append(reply_type)
            mock_state_manager.save()

        # After 10 replies, should have used multiple types
        assert len(types_used) >= 3
