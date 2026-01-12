"""Groq LLM provider implementation - FREE tier with Llama models."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import LLMProviderError
from twitter_bot.generation.provider import GenerationResult, LLMProvider


class GroqProvider(LLMProvider):
    """Groq LLM provider - FREE tier using Llama 3.3 70B."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        if not api_key:
            raise LLMProviderError("Groq API key is required")

        self.model_name = model
        self._api_key = api_key
        self._base_url = "https://api.groq.com/openai/v1"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def generate(self, prompt: str, max_tokens: int = 500) -> GenerationResult:
        """Generate text from a prompt."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.8,
                    },
                )
                response.raise_for_status()
                data = response.json()

            text = data["choices"][0]["message"]["content"]
            if not text:
                raise LLMProviderError("Empty response from Groq")

            return GenerationResult(
                text=text,
                model=self.model_name,
            )
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(f"Groq API error: {e.response.text}") from e
        except Exception as e:
            raise LLMProviderError(f"Groq generation failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def generate_multiple(
        self, prompt: str, n: int = 3, max_tokens: int = 500
    ) -> list[GenerationResult]:
        """Generate multiple completions."""
        results = []
        temperatures = [0.7, 0.8, 0.9, 1.0, 1.1][:n]

        for temp in temperatures:
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(
                        f"{self._base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model_name,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": temp,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                text = data["choices"][0]["message"]["content"]
                if text:
                    results.append(
                        GenerationResult(
                            text=text,
                            model=self.model_name,
                        )
                    )
            except Exception:
                continue

        if not results:
            raise LLMProviderError("All Groq generation attempts failed")

        return results
