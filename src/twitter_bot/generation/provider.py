"""LLM provider protocol for abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """Result from LLM generation."""

    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 500) -> GenerationResult:
        """Generate text from a prompt.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response

        Returns:
            GenerationResult with generated text and metadata
        """
        pass

    @abstractmethod
    def generate_multiple(
        self, prompt: str, n: int = 3, max_tokens: int = 500
    ) -> list[GenerationResult]:
        """Generate multiple completions from a prompt.

        Args:
            prompt: The prompt to send to the LLM
            n: Number of completions to generate
            max_tokens: Maximum tokens per response

        Returns:
            List of GenerationResults
        """
        pass
