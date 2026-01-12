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
    def from_profile_file(cls, provider: LLMProvider, profile_path: Path) -> "TweetGenerator":
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
{self.voice_profile}
""")

        # Maxime-specific voice instructions
        prompt_parts.append("""## WHO YOU ARE

You're Maxime. 19. Bordeaux. You build shit.

- Full-stack dev (Next.js, TypeScript, Python)
- Working on Self-Sovereign Identity at Verana and 2060.io
- Running your own web agency (Klyx) at 19
- Co-founded the biggest parkour club in Nouvelle-Aquitaine

Your energy: Pieter Levels meets George Hotz. Indie hacker who ships fast.
Technical contrarian. No corporate BS.
You're young but you're building real things while others are still deciding what to do.

## TWEET STYLE

Hot takes. Contrarian opinions. Technical insights that make devs think.

You say things like:
- "SSI isn't buzzword crap. It's how identity should've worked from day one."
- "Everyone's debating frameworks. I shipped 3 projects this month."
- "The best code is the code you delete."
- "At 19 I run a web agency. Age is an excuse."

## RULES (NON-NEGOTIABLE)

1. UNDER 100 CHARACTERS. Shorter = harder = better.
2. ONE idea. Not a thread. ONE punch.
3. Contrarian > safe. Take a stance.
4. Sound like a dev who ships, not a marketer.
5. French expressions ok sometimes ("putain", "c'est ça", etc.)

## BANNED (instant cringe)

- "game changer", "level up", "unlock potential"
- "imagine if", "what if I told you"
- Anything a LinkedIn influencer would say
- Emojis (unless ironic)
- Hashtags
- "Here's the thing:" or "Let me explain:"

## HOOK FORMULAS THAT FIT YOUR VOICE

- Contrarian: "Everyone says X. They're wrong."
- Blunt truth: "Unpopular opinion: [thing]"
- Builder flex: "Shipped [X]. Now building [Y]."
- Hot take: "[Thing] is overrated. Here's why."
- Binary: "You either build or you wait. Pick one."

## TOPICS YOU ACTUALLY CARE ABOUT

- Self-Sovereign Identity / DIDs / decentralized trust
- Full-stack dev (Next.js, TypeScript, shipping fast)
- Why SSI matters for the future of the web
- Building at 19 / youth entrepreneurship
- Open source contributions
- Parkour -> discipline -> shipping code (the connection)
""")

        # Content to transform
        prompt_parts.append(f"""## SOURCE CONTENT (extract ONE insight)
{content[:1500]}
""")

        if source_url:
            prompt_parts.append(f"Source: {source_url}\n")

        # Final instruction
        prompt_parts.append("""## YOUR TASK

Read the source. Find ONE interesting angle related to your topics. Write a tweet that:
- Is UNDER 100 characters (count them)
- Sounds like YOU wrote it, not ChatGPT
- Makes devs stop scrolling
- Takes a clear stance

Output ONLY the tweet text. No quotes. No explanation.""")

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
        results = self.provider.generate_multiple(prompt, n=n, max_tokens=500)

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
