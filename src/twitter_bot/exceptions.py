"""Custom exception hierarchy for twitter-bot."""


class TwitterBotError(Exception):
    """Base exception for all twitter-bot errors."""

    pass


class ConfigError(TwitterBotError):
    """Configuration-related errors."""

    pass


class TwitterAPIError(TwitterBotError):
    """Twitter API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class LLMProviderError(TwitterBotError):
    """LLM provider errors."""

    pass


class SourceError(TwitterBotError):
    """Content source errors (RSS, web, YouTube)."""

    pass


class StateError(TwitterBotError):
    """State persistence errors."""

    pass
