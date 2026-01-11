"""Tweet generator using LLM provider and voice profile."""

from dataclasses import dataclass
from pathlib import Path

from twitter_bot.generation.provider import LLMProvider


@dataclass
class TweetDraft:
    """A generated tweet draft."""

    content: str
    hook_type: str | None = None
    source_url: str | None = None


class TweetGenerator:
    """Generates tweets using LLM with voice matching."""

    def __init__(self, provider: LLMProvider, voice_profile: str | None = None):
        self.provider = provider
        self.voice_profile = voice_profile or ""

    @classmethod
    def from_profile_file(
        cls, provider: LLMProvider, profile_path: Path
    ) -> "TweetGenerator":
        """Create generator with voice profile from file."""
        voice_profile = ""
        if profile_path.exists():
            voice_profile = profile_path.read_text()
        return cls(provider, voice_profile)

    def _build_prompt(
        self,
        content: str,
        source_url: str | None = None,
        style_hint: str | None = None,
    ) -> str:
        """Build the generation prompt."""
        prompt_parts = []

        # Voice profile context
        if self.voice_profile:
            prompt_parts.append(f"""## Voice Profile
You are writing tweets as this person. Match their voice, style, and perspective:

{self.voice_profile}
""")

        # Core instructions
        prompt_parts.append("""## Tweet Writing Rules

1. Keep tweets under 280 characters
2. Use a strong hook in the first line
3. Be opinionated and take a clear stance
4. Sound human, not like AI - use casual language
5. No hashtags unless absolutely necessary
6. No emojis unless it fits the voice naturally
7. Make it shareable - would someone screenshot this?

## Hook Types (rotate between these):
- Bold statement: "Nobody talks about this, but..."
- Contrarian: "Everyone says X. They're wrong."
- Number hook: "3 things I learned about..."
- Pattern interrupt: Start with an unexpected observation
- Personal story: "I just realized..." or "Today I..."
""")

        # Content to transform
        prompt_parts.append(f"""## Source Content to Transform

{content}

""")

        if source_url:
            prompt_parts.append(f"Source URL: {source_url}\n\n")

        if style_hint:
            prompt_parts.append(f"Style hint: {style_hint}\n\n")

        # Final instruction
        prompt_parts.append("""## Your Task

Write a single tweet based on the source content above. Extract the most interesting insight
and present it in a way that:
- Sounds like the voice profile (if provided)
- Uses one of the hook types
- Is under 280 characters
- Would make developers stop scrolling

Output ONLY the tweet text, nothing else. No quotes, no explanation.""")

        return "\n".join(prompt_parts)

    def generate_drafts(
        self,
        content: str,
        source_url: str | None = None,
        n: int = 3,
    ) -> list[TweetDraft]:
        """Generate multiple tweet drafts from content.

        Args:
            content: Source content to transform into tweets
            source_url: Optional URL of the source
            n: Number of drafts to generate

        Returns:
            List of TweetDraft objects
        """
        prompt = self._build_prompt(content, source_url)
        results = self.provider.generate_multiple(prompt, n=n, max_tokens=150)

        drafts = []
        for result in results:
            # Clean up the response
            tweet_text = result.text.strip()
            # Remove surrounding quotes if present
            if tweet_text.startswith('"') and tweet_text.endswith('"'):
                tweet_text = tweet_text[1:-1]
            # Truncate if over 280
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."

            drafts.append(
                TweetDraft(
                    content=tweet_text,
                    source_url=source_url,
                )
            )

        return drafts

    def generate_single(
        self,
        content: str,
        source_url: str | None = None,
    ) -> TweetDraft:
        """Generate a single tweet draft."""
        drafts = self.generate_drafts(content, source_url, n=1)
        return drafts[0] if drafts else TweetDraft(content="")
