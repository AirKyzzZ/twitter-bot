"""Gemini LLM provider implementation using google-genai SDK."""

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from twitter_bot.exceptions import LLMProviderError
from twitter_bot.generation.provider import GenerationResult, LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not api_key:
            raise LLMProviderError("Gemini API key is required")

        self.model_name = model
        self._client = genai.Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def generate(self, prompt: str, max_tokens: int = 500) -> GenerationResult:
        """Generate text from a prompt."""
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.8,
                ),
            )

            if not response.text:
                raise LLMProviderError("Empty response from Gemini")

            return GenerationResult(
                text=response.text,
                model=self.model_name,
            )
        except Exception as e:
            if "API key" in str(e):
                raise LLMProviderError(f"Invalid Gemini API key: {e}") from e
            raise LLMProviderError(f"Gemini generation failed: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True,
    )
    def generate_multiple(
        self, prompt: str, n: int = 3, max_tokens: int = 500
    ) -> list[GenerationResult]:
        """Generate multiple completions.

        Note: Gemini doesn't natively support n completions,
        so we make multiple calls with varied temperature.
        """
        results = []
        temperatures = [0.7, 0.8, 0.9, 1.0, 1.1][:n]

        for temp in temperatures:
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=max_tokens,
                        temperature=temp,
                    ),
                )

                if response.text:
                    results.append(
                        GenerationResult(
                            text=response.text,
                            model=self.model_name,
                        )
                    )
            except Exception:
                # Continue with other generations if one fails
                continue

        if not results:
            raise LLMProviderError("All Gemini generation attempts failed")

        return results
