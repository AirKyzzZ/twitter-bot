"""Tweet generator using LLM provider and voice profile."""

import random
from dataclasses import dataclass, field
from pathlib import Path

from twitter_bot.generation.provider import LLMProvider


@dataclass
class TweetDraft:
    """A generated tweet draft."""

    content: str
    hook_type: str | None = None
    source_url: str | None = None
    is_thread: bool = False
    thread_parts: list[str] = field(default_factory=list)
    suggested_image: str | None = None  # Description of suggested image/meme


# Tweet format types for variety
TWEET_FORMATS = [
    "hot_take",
    "insight",
    "question",
    "story",
    "tip",
    "observation",
    "thread",
    "controversial",
    "builder_update",
    "behind_scenes",
]


class TweetGenerator:
    """Generates tweets using LLM with voice matching."""

    def __init__(
        self,
        provider: LLMProvider,
        voice_profile: str | None = None,
        recent_tweets: list[str] | None = None,
    ):
        self.provider = provider
        self.voice_profile = voice_profile or ""
        self.recent_tweets = recent_tweets or []

    @classmethod
    def from_profile_file(
        cls,
        provider: LLMProvider,
        profile_path: Path,
        recent_tweets: list[str] | None = None,
    ) -> "TweetGenerator":
        """Create generator with voice profile from file."""
        voice_profile = ""
        if profile_path.exists():
            voice_profile = profile_path.read_text()
        return cls(provider, voice_profile, recent_tweets)

    def _build_prompt(
        self,
        content: str,
        source_url: str | None = None,
        style_hint: str | None = None,
        allow_thread: bool = True,
        suggest_image: bool = True,
    ) -> str:
        """Build the generation prompt."""
        prompt_parts = []

        # Voice profile context
        if self.voice_profile:
            prompt_parts.append(f"""## Voice Profile
{self.voice_profile}
""")

        # Suggested format for this tweet (for variety)
        suggested_format = random.choice(TWEET_FORMATS)
        if not allow_thread and suggested_format == "thread":
            suggested_format = random.choice([f for f in TWEET_FORMATS if f != "thread"])

        # Maxime-specific voice instructions
        prompt_parts.append(f"""## WHO YOU ARE

You're Maxime. 19. Bordeaux. You build shit.

- Full-stack dev (Next.js, TypeScript, Python)
- Working on Self-Sovereign Identity at Verana and 2060.io
- Running your own web agency (Klyx) at 19
- Co-founded the biggest parkour club in Nouvelle-Aquitaine

Your energy: Pieter Levels meets George Hotz. Indie hacker who ships fast.
Technical contrarian. No corporate BS.
You're young but you're building real things while others are still deciding what to do.

## YOUR TWEET STYLE

VARIETY is key. You don't sound like a bot. You mix up:

**Hot Takes** (controversial, makes people think):
- "SSI isn't buzzword crap. It's how identity should've worked from day one."
- "90% of 'AI startups' are just wrapper products. Build the infrastructure instead."
- "Framework debates are cope. Ship something."

**Genuine Insights** (teach something real):
- "The trick with DIDs: treat them like phone numbers, not like GPG keys. Users don't care about crypto."
- "Most auth is broken because we trust servers, not users. SSI flips that."
- "Next.js 15 server components actually matter. Here's what changed for my agency work..."

**Questions** (engagement bait that's authentic):
- "Honest question: who's actually using DIDs in production? DM me, wanna compare notes."
- "What's stopping you from shipping? Genuinely curious."
- "Best decision I made at 19? Starting. What's yours?"

**Builder Updates** (show, don't tell):
- "Just deployed a DID resolver in 47 lines of TypeScript. Clean code > clever code."
- "3 client sites shipped this week. Agency life hits different when you're 19."
- "Built a credential wallet prototype this weekend. SSI is clicking."

**Stories** (personal, relatable):
- "Parkour taught me something: you either commit to the jump or you don't. Same with shipping."
- "First time a client called me 'too young' I was 17. Shipped their project in 2 weeks."
- "Failed my first startup at 16. Best thing that happened to me."

**Behind the Scenes** (authentic glimpses):
- "Current setup: VSCode, Spotify lo-fi, 3 client projects open. The grind."
- "Just spent 2 hours debugging a race condition. Found it. It was my own code from last month."
- "Reading about Verifiable Credentials at 2am. This is the future and nobody's paying attention."

**Tips** (actionable value):
- "Skip tutorials. Read source code. You'll learn 10x faster."
- "One Next.js trick: prefetch on hover, not on render. Your LCP will thank you."
- "Want to understand SSI? Start with DIDs, ignore everything else for now."

## RULES

1. MAX 280 CHARACTERS for single tweets (use the space wisely when you have something real to say)
2. Vary length: some tweets are punchy (50-100 chars), others dive deeper (150-280 chars)
3. Sound like a 19-year-old dev who ships, not a marketer or AI
4. Be specific over generic. "Shipped 47 lines" > "Shipped some code"
5. STRICTLY ENGLISH only. No French words.
6. Take stances. Lukewarm takes get no engagement.

## BANNED (instant cringe)

- "game changer", "level up", "unlock your potential"
- "imagine if", "what if I told you", "here's the thing"
- Anything a LinkedIn influencer would say
- Excessive emojis (one or zero max, and only if natural)
- Hashtags (never)
- "Let me explain:", "Thread:", "1/n"
- Generic motivational crap
- Starting with "Just" or "So"

## FORMAT SUGGESTION FOR THIS TWEET: {suggested_format.upper()}

Use this format as inspiration, but if the content calls for something else, go with that.
""")

        # Recent tweets context to avoid repetition
        if self.recent_tweets:
            recent_context = "\n".join(f"- {t}" for t in self.recent_tweets[-5:])
            prompt_parts.append(f"""## YOUR RECENT TWEETS (DON'T REPEAT PATTERNS)

{recent_context}

IMPORTANT: Your new tweet must be DIFFERENT from these. Avoid:
- Same sentence structures (if you said "X > Y", don't do that pattern again)
- Same topics (if you just talked about decentralization, talk about something else)
- Same length/format (if last tweets were all short, try something longer and vice versa)
""")

        # Content to transform
        prompt_parts.append(f"""## SOURCE CONTENT
{content[:2000]}
""")

        if source_url:
            prompt_parts.append(f"Source: {source_url}\n")

        # Thread option
        thread_instruction = ""
        if allow_thread:
            thread_instruction = """
**THREAD OPTION**: If this content is rich enough (tutorial, deep insight, story), you can write a 2-4 tweet thread.
Format threads as:
THREAD:
1. [First tweet - the hook, max 280 chars]
2. [Second tweet - the meat, max 280 chars]
3. [Third tweet - conclusion or call to action, max 280 chars]

Only use threads for substantial content. Most tweets should be single."""

        # Image suggestion
        image_instruction = ""
        if suggest_image:
            image_instruction = """
**IMAGE SUGGESTION**: If a meme or image would make this tweet pop, add at the end:
[IMAGE: brief description of the image/meme that would work]
Examples: [IMAGE: Drake meme - "Learning from tutorials" vs "Reading source code"]
Only suggest images when they genuinely add value. Most tweets don't need images."""

        # Final instruction
        prompt_parts.append(f"""## YOUR TASK

Read the source content. Find an interesting angle related to your world (dev, SSI, building, agency life, being young).
{thread_instruction}
{image_instruction}

Write a tweet that:
- Fits within 280 characters (single tweet) OR is a properly formatted thread
- Sounds authentically like YOU, not generic AI
- Makes devs/builders stop scrolling
- Takes a clear stance or provides real value
- Is DIFFERENT from your recent tweets in structure and topic

Output ONLY the tweet text (or THREAD: format). No quotes. No explanation.""")

        return "\n".join(prompt_parts)

    def _parse_response(self, text: str, source_url: str | None = None) -> TweetDraft:
        """Parse LLM response into a TweetDraft, handling threads and images."""
        text = text.strip()

        # Remove surrounding quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        # Check for image suggestion
        suggested_image = None
        if "[IMAGE:" in text:
            import re

            image_match = re.search(r"\[IMAGE:\s*([^\]]+)\]", text)
            if image_match:
                suggested_image = image_match.group(1).strip()
                text = re.sub(r"\s*\[IMAGE:[^\]]+\]", "", text).strip()

        # Check for thread format
        is_thread = False
        thread_parts = []

        if text.upper().startswith("THREAD:"):
            is_thread = True
            thread_content = text[7:].strip()  # Remove "THREAD:"

            # Parse numbered tweets
            import re

            parts = re.split(r"\n\s*\d+\.\s*", thread_content)
            thread_parts = [p.strip() for p in parts if p.strip()]

            # Validate each part is within limits
            thread_parts = [p[:280] for p in thread_parts]

            # Main content is the first tweet
            content = thread_parts[0] if thread_parts else text
        else:
            content = text
            # Truncate if over 280
            if len(content) > 280:
                content = content[:277] + "..."

        return TweetDraft(
            content=content,
            source_url=source_url,
            is_thread=is_thread,
            thread_parts=thread_parts,
            suggested_image=suggested_image,
        )

    def generate_drafts(
        self,
        content: str,
        source_url: str | None = None,
        n: int = 3,
        allow_thread: bool = True,
        suggest_image: bool = True,
    ) -> list[TweetDraft]:
        """Generate multiple tweet drafts from content.

        Args:
            content: Source content to transform into tweets
            source_url: Optional URL of the source
            n: Number of drafts to generate
            allow_thread: Whether to allow thread generation
            suggest_image: Whether to ask for image suggestions

        Returns:
            List of TweetDraft objects
        """
        prompt = self._build_prompt(
            content,
            source_url,
            allow_thread=allow_thread,
            suggest_image=suggest_image,
        )
        results = self.provider.generate_multiple(prompt, n=n, max_tokens=800)

        drafts = []
        for result in results:
            draft = self._parse_response(result.text, source_url)
            drafts.append(draft)

        return drafts

    def generate_single(
        self,
        content: str,
        source_url: str | None = None,
        allow_thread: bool = True,
        suggest_image: bool = True,
    ) -> TweetDraft:
        """Generate a single tweet draft."""
        drafts = self.generate_drafts(
            content,
            source_url,
            n=1,
            allow_thread=allow_thread,
            suggest_image=suggest_image,
        )
        return drafts[0] if drafts else TweetDraft(content="")
