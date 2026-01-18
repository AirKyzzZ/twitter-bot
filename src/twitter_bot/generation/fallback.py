"""Fallback LLM provider that chains multiple providers with automatic failover."""

import logging
from datetime import UTC, datetime, timedelta

from twitter_bot.exceptions import LLMProviderError
from twitter_bot.generation.provider import GenerationResult, LLMProvider

logger = logging.getLogger(__name__)


class FallbackProvider(LLMProvider):
    """LLM provider that falls back to secondary providers on rate limits.

    Tries providers in order, switching to the next when rate limited.
    Remembers rate limit status to avoid repeated failures.
    """

    def __init__(self, providers: list[tuple[str, LLMProvider]]):
        """Initialize with a list of named providers.

        Args:
            providers: List of (name, provider) tuples in priority order
        """
        if not providers:
            raise LLMProviderError("At least one provider is required")

        self.providers = providers
        self._rate_limited_until: dict[str, datetime] = {}

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an error is a rate limit error."""
        error_str = str(error).lower()
        return any(
            indicator in error_str
            for indicator in ["rate limit", "rate_limit", "too many requests", "429"]
        )

    def _get_available_provider(self) -> tuple[str, LLMProvider] | None:
        """Get the first provider that isn't currently rate limited."""
        now = datetime.now(UTC)

        for name, provider in self.providers:
            # Check if this provider is rate limited
            if name in self._rate_limited_until:
                if now < self._rate_limited_until[name]:
                    logger.debug(f"{name} is rate limited, skipping")
                    continue
                else:
                    # Rate limit expired
                    del self._rate_limited_until[name]

            return name, provider

        return None

    def _mark_rate_limited(self, name: str, duration_minutes: int = 60) -> None:
        """Mark a provider as rate limited for a duration."""
        self._rate_limited_until[name] = datetime.now(UTC) + timedelta(
            minutes=duration_minutes
        )
        logger.warning(f"{name} rate limited, will retry in {duration_minutes} minutes")

    def generate(self, prompt: str, max_tokens: int = 500) -> GenerationResult:
        """Generate text, falling back to secondary providers on rate limits."""
        errors = []

        for name, provider in self.providers:
            # Skip rate-limited providers
            if name in self._rate_limited_until:
                now = datetime.now(UTC)
                if now < self._rate_limited_until[name]:
                    continue
                else:
                    del self._rate_limited_until[name]

            try:
                logger.info(f"Generating with {name}")
                result = provider.generate(prompt, max_tokens)
                return result

            except LLMProviderError as e:
                if self._is_rate_limit_error(e):
                    self._mark_rate_limited(name)
                    errors.append(f"{name}: rate limited")
                    continue
                else:
                    errors.append(f"{name}: {e}")
                    continue

            except Exception as e:
                errors.append(f"{name}: {e}")
                continue

        raise LLMProviderError(f"All providers failed: {'; '.join(errors)}")

    def generate_multiple(
        self, prompt: str, n: int = 3, max_tokens: int = 500
    ) -> list[GenerationResult]:
        """Generate multiple completions with fallback support."""
        errors = []

        for name, provider in self.providers:
            # Skip rate-limited providers
            if name in self._rate_limited_until:
                now = datetime.now(UTC)
                if now < self._rate_limited_until[name]:
                    continue
                else:
                    del self._rate_limited_until[name]

            try:
                logger.info(f"Generating {n} completions with {name}")
                results = provider.generate_multiple(prompt, n, max_tokens)
                return results

            except LLMProviderError as e:
                if self._is_rate_limit_error(e):
                    self._mark_rate_limited(name)
                    errors.append(f"{name}: rate limited")
                    continue
                else:
                    errors.append(f"{name}: {e}")
                    continue

            except Exception as e:
                errors.append(f"{name}: {e}")
                continue

        raise LLMProviderError(f"All providers failed: {'; '.join(errors)}")
