"""Tweet generator using LLM provider and voice profile."""

import random
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
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
# DATA-DRIVEN: Short punchy content massively outperforms threads (14x more reach)
SHORT_FORMATS = [
    "hot_take",          # Spicy opinion on current tech news
    "observation",       # Quick insight from building/shipping
    "one_liner",         # 1-2 sentence punch
    "reaction",          # React to news/announcement (time-sensitive)
    "unpopular_opinion", # Contrarian view that sparks debate
]

# DISABLED: Analytics show 0 threads in top 27 performers
THREAD_FORMATS: list[str] = []  # Threads don't work - disabled

STANDARD_FORMATS = [
    "personal_update",   # What you're building/shipping
    "quick_tip",         # Short actionable advice
    "question",          # Provocative question to audience
    "behind_scenes",     # Real moment from your work
]

TWEET_FORMATS = SHORT_FORMATS + STANDARD_FORMATS  # No threads


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

        # Determine Format and Constraints
        # DATA-DRIVEN: Short punchy content gets 2x more impressions than long-form
        # Threads are DISABLED (0 threads in top 27 performers)
        # Distribution: 70% short, 30% standard, 0% threads
        roll = random.random()
        if roll < 0.70:
            category = "SHORT"
            suggested_format = random.choice(SHORT_FORMATS)
        else:
            category = "STANDARD"
            suggested_format = random.choice(STANDARD_FORMATS)

        # Add variety by rotating opening styles
        # DATA-DRIVEN: Removed "X vs Y comparison" - it produces 7.1 avg impressions
        opening_styles = [
            "Start with a SHORT provocative question",
            "Start with a quick personal anecdote (one sentence max)",
            "Start with a bold, slightly spicy claim",
            "Start with a raw observation (under 15 words)",
            "Start by calling out something that's BS",
            "React to the news/content with your genuine take",
            "Start with dry humor or irony",
        ]
        selected_opening = random.choice(opening_styles)

        # Maxime-specific voice instructions - DATA-DRIVEN REWRITE + E.H.A FORMAT
        prompt_parts.append(f"""## OPENING STYLE FOR THIS TWEET
**{selected_opening}**

## E.H.A FRAMEWORK (Emotion + Hook + Action)

Every tweet must follow E.H.A:
1. **EMOTION**: Trigger an emotional response (awe, humor, controversy, relatability)
2. **HOOK**: First phrase stops the scroll (bold claim, question, number, story)
3. **ACTION**: Make it share-worthy (insight worth spreading, relatable truth)

Examples of E.H.A:
- "spent 6 hours debugging a typo" (humor + relatable + share-worthy)
- "hot take: 90% of 'best practices' are cargo cult" (controversy + bold + discussion-worthy)
- "shipped at 3am, woke up to 200 signups" (awe + story + inspiring)

## WHO YOU ARE

You're Maxime. 19. Bordeaux. You build stuff.

**Quick facts:**
- Stack: Next.js, TypeScript, Python, K8s. Harvard CS50 grad.
- Work: Verana (Trust Network), 2060.io (SSI/DIDComm), Klyx (your agency)
- Life: Co-founded PKBA (parkour club), active in GDG Bordeaux

## YOUR ACTUAL TWITTER VOICE (Jan 2026 analytics)

Based on what ACTUALLY performs (from 558 tweets analyzed):

**SHORT & PUNCHY wins:**
- "markdown files have never been more valuable" (44 impressions)
- "smart contracts are just fancy if-else statements" (21 impressions)
- "nlp models still can't handle sarcasm" (20 impressions)

**Replies massively outperform original tweets:**
- Your top 25 are ALL replies, not original tweets
- Best original tweet: 44 impressions vs best reply: 6242 impressions
- 62% of your original tweets get <10 impressions

**What works in original tweets:**
- One-liner observations with dry humor
- Specific tech takes (not generic "X is the future")
- Personal experiences with real details

## WHAT DOESN'T WORK (UPDATED Jan 2026)

These patterns STILL average <10 impressions despite being banned:
- ❌ "You're either X or Y" (73 tweets, 8.0 avg - DEAD)
- ❌ "Most people/devs do X" (47 tweets, 8.9 avg - DEAD)
- ❌ "I've spent X hours..." (11 tweets, 8.9 avg - DEAD)
- ❌ "like it's 2010" comparisons (all <10 impressions)
- ❌ "90% of X are Y" statistics (all <10 impressions)
- ❌ Multi-paragraph thought pieces (171 tweets got <10 impressions)

## RULES

1. **KEEP IT SHORT.** Under 140 chars is ideal. Under 80 is gold
2. **Be specific.** Real projects, real numbers, real experiences
3. **Sound like yourself.** 19yo dev texting a friend, not a LinkedIn coach
4. **Hot takes > generic advice.** Take a stance
5. **No hashtags. Ever**
6. **Lowercase always.** No trailing periods or commas
7. **Complete thoughts only.** Never cut off mid-sentence

## BANNED PHRASES (automatic fail - these get <10 impressions)

- "You're either X or Y", "Most people do X", "The winners..."
- "I've spent X hours", "Here's what I learned", "I've analyzed X"
- "game changer", "level up", "unlock", "ahead of the curve"
- "getting left behind", "This proves that", "This kills the old way"
- "The best part?", "But here's the catch", "Who's with me?"
- "You're about to witness", "You're about to unlock"
- "like it's 2010", "X% of Y are Z", "prove me wrong"
- "What's your next move?", "What if you could"
- Any multi-part thread structure ("1/", "Thread:", "Here's a breakdown")
- Summarizing content like a news bot
- Generic motivational content
- Excessive emojis (0-1 max)
- Starting with "Just", "So", or "Are you still"

## FORMAT: {suggested_format.upper()}
   
   """)

        # Add constraints based on category
        if category == "SHORT":
            prompt_parts.append("""
**CONSTRAINT: SHORT & PUNCHY**
- Maximum 140 characters. Ideally under 80.
- No filler words.
- One single thought, observation, or question.
- No bullet points, no lists.
- Think: tweet you'd send to a friend, not a blog post.
""")
        # THREADS DISABLED - data shows 0 threads in top performers

        # Recent tweets context to avoid repetition - use last 15 for better coverage
        if self.recent_tweets:
            recent_context = "\n".join(f"- {t[:150]}..." if len(t) > 150 else f"- {t}" for t in self.recent_tweets[-15:])
            prompt_parts.append(f"""## YOUR RECENT TWEETS (DON'T REPEAT PATTERNS)

{recent_context}

CRITICAL - Your new tweet must be COMPLETELY DIFFERENT:
- NO similar openings (if recent tweets start with "You're about...", start differently)
- NO same sentence structures (vary between questions, statements, stories)
- NO same hooks (if you used "This proves...", try a story or question instead)
- If recent tweets were long, make this one SHORT and punchy
- If recent tweets were threads, make this a single killer tweet
""")

        # Content to transform
        prompt_parts.append(f"""## SOURCE CONTEXT
{content[:2000]}
""")

        if source_url:
            prompt_parts.append(f"Source: {source_url}\n")

        # THREADS DISABLED - no thread instructions needed

        # Image suggestion - 40% of tweets should have images (2x algo boost!)
        image_instruction = ""
        if suggest_image:
            # 50% of tweets get mandatory image prompt
            should_suggest_image = random.random() < 0.50
            # DEBUG: For now, always suggest image to test
            should_suggest_image = True  # TEMP: force all tweets to have images
            if should_suggest_image:
                image_instruction = """
**🖼️ THIS TWEET MUST HAVE AN IMAGE** (non-negotiable):
End your tweet with [IMAGE: description]. This is REQUIRED.

Image ideas:
- Meme format (describe it): "drake meme - top: writing tests, bottom: console.log debugging"
- Tech aesthetic: "laptop with code on screen, coffee, dark mode"
- Reaction: "confused developer looking at screen"
- Screenshot: "terminal with error message"

FORMAT: your tweet text here [IMAGE: your image description]
Example: "ai just wrote my entire app. it doesn't work but it's there [IMAGE: code editor full of red squiggly lines]"
"""
            else:
                image_instruction = """
**IMAGE (optional)**: If a meme or screenshot would genuinely help, add:
[IMAGE: brief description]
"""

        # Final instruction - DATA-DRIVEN rewrite
        prompt_parts.append(f"""## YOUR TASK

Use the SOURCE CONTEXT as inspiration (not to summarize).

**DO:**
- Extract ONE interesting angle or hot take
- React with YOUR genuine perspective
- Keep it SHORT (under 140 chars ideal, under 80 gold)
- Sound like you're texting a dev friend

**DON'T:**
- Summarize the content like a news bot
- Use any banned patterns ("You're either...", "Most people...", etc.)
- Write a thread or multi-part post
- Sound like a LinkedIn thought leader
- Force an SSI angle unless it's actually about identity

{image_instruction}

**SINGLE TWEET ONLY.** Keep it {category.lower()}.

Output ONLY the tweet text. No quotes. No explanation. No meta-commentary.""")

        return "\n".join(prompt_parts)

    def _truncate_at_word_boundary(self, text: str, max_length: int = 280) -> str:
        """Truncate text at word boundary, preserving complete sentences when possible."""
        if len(text) <= max_length:
            return text

        # Try to find a sentence boundary first (. ! ?)
        truncated = text[:max_length]

        # Look for last sentence boundary within limit
        for punct in [". ", "! ", "? "]:
            last_sentence = truncated.rfind(punct)
            if last_sentence > max_length * 0.5:  # At least 50% of content
                return truncated[: last_sentence + 1].strip()

        # No good sentence boundary - find last word boundary
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.7:  # At least 70% of content
            return truncated[:last_space].strip()

        # Fallback: just use character limit minus some buffer
        return truncated.strip()

    def _strip_trailing_punctuation(self, text: str) -> str:
        """Remove trailing dots and commas for a cleaner, more casual style."""
        text = text.rstrip()
        # Strip trailing periods and commas (but keep ? and ! for questions/exclamations)
        while text and text[-1] in '.,':
            text = text[:-1].rstrip()
        return text

    def _parse_response(self, text: str, source_url: str | None = None) -> TweetDraft:
        """Parse LLM response into a TweetDraft, handling threads and images."""
        text = text.strip()

        # Remove surrounding quotes if present
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        # Check for image suggestion
        suggested_image = None
        if "[IMAGE:" in text:
            image_match = re.search(r"\[IMAGE:\s*([^\]]+)\]", text)
            if image_match:
                suggested_image = image_match.group(1).strip()
                text = re.sub(r"\s*\[IMAGE:[^\]]+\]", "", text).strip()

        # Check for thread format
        is_thread = False
        thread_parts = []

        # Normalize text for detection
        clean_text = text.strip()

        if clean_text.upper().startswith("THREAD:"):
            is_thread = True
            thread_content = clean_text[7:].strip()
        elif re.match(r"^1[./)]", clean_text):
            is_thread = True
            thread_content = clean_text
        else:
            thread_content = clean_text

        if is_thread:
            # Parse numbered tweets
            # Matches "1.", "1/", "1/6", "1 of 6", "1)", "\n2.", etc.
            parts = re.split(r"(?:^|\n)\s*\d+\s*(?:[./)]|of|/)\s*(?:\d+\s*)?", thread_content)
            thread_parts = [p.strip() for p in parts if p.strip()]

            # Limit thread to 5 tweets max
            thread_parts = thread_parts[:5]

            # Truncate each part at word boundary and strip trailing punctuation
            thread_parts = [
                self._strip_trailing_punctuation(self._truncate_at_word_boundary(p, 280))
                for p in thread_parts
            ]

            # Main content is the first tweet
            content = thread_parts[0] if thread_parts else text
        else:
            content = text
            # Truncate at word boundary if over 280
            if len(content) > 280:
                content = self._truncate_at_word_boundary(content, 280)

        # Strip trailing dots and commas for cleaner style
        content = self._strip_trailing_punctuation(content)

        return TweetDraft(
            content=content,
            source_url=source_url,
            is_thread=is_thread,
            thread_parts=thread_parts,
            suggested_image=suggested_image,
        )

    # Overused phrases to detect and reject
    # DATA-DRIVEN: These patterns average <10 impressions (updated Jan 2026)
    OVERUSED_PATTERNS = [
        # The deadly "Binary" pattern (8.0 avg impressions across 73 tweets)
        r"you.?re either .+ or",  # Matches you're, youre, you're (curly)
        # The "Most people" pattern (8.9 avg impressions across 47 tweets)
        r"most people .+\. the winners",
        r"most people .+\. you",
        r"most people think",
        r"most people don't",
        r"most devs ",
        r"most developers ",
        r"most frontend devs",
        r"most backend devs",
        # The "Data Flex" pattern (8.9 avg impressions)
        r"i've spent \d+ hours",
        r"i spent \d+ hours",
        r"i've analyzed \d+",
        r"i analyzed \d+",
        r"here's what i learned",
        r"here's what i've learned",
        r"here's what i found",
        # LinkedIn energy (all <15 impressions)
        r"you're about to witness",
        r"you're about to unlock",
        r"this proves that",
        r"this kills the old way",
        r"getting left behind",
        r"ahead of the curve",
        r"the best part\?",
        r"but here's the catch",
        r"what.?s your next move",  # Matches with or without "so" prefix
        r"who's with me\?",
        r"let me explain",
        r"game.?changer",
        r"level up",
        r"unlock your",
        r"what if you could",
        r"the winners know",
        r"the winners are",
        r"the winners,? however",
        # Generic tech hot takes that fail (<10 impressions)
        r"like it's 2010",
        r"still building .+ like it's",
        r"you're still using",
        r"you're still building",
        r"are you still",
        r"90% of .+ are",
        r"80% of .+ are",
        r"\d+% of .+ fail",
        r"prove me wrong",
        # Overused question starters (anchored)
        r"^what if you",
        r"^so,? how do you",
        # Thread starters (threads don't work)
        r"^\s*thread:",
        r"^\s*\d+[/.]",
        r"^\s*1\)",
        # Generic closers
        r"which one are you",
        r"you're either building .+ or you're",
    ]

    def _is_too_similar(self, content: str, threshold: float = 0.5) -> bool:
        """Check if content is too similar to recent tweets or uses overused patterns."""
        content_lower = content.lower()

        # Check for overused patterns
        for pattern in self.OVERUSED_PATTERNS:
            if re.search(pattern, content_lower):
                return True

        # Check similarity against recent tweets (lowered threshold from 0.6 to 0.5)
        for past_tweet in self.recent_tweets:
            ratio = SequenceMatcher(None, content.lower(), past_tweet.lower()).ratio()
            if ratio > threshold:
                return True

            # Also check if they share the same opening phrase (first 50 chars)
            if len(content) > 50 and len(past_tweet) > 50:
                opening_ratio = SequenceMatcher(
                    None, content_lower[:50], past_tweet.lower()[:50]
                ).ratio()
                if opening_ratio > 0.7:  # Same opening = too similar
                    return True

        return False

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
            content: Source content OR Topic/Concept
            source_url: Optional URL of the source (None implies topic-based generation)
            n: Number of drafts to generate
            allow_thread: Whether to allow thread generation
            suggest_image: Whether to ask for image suggestions

        Returns:
            List of TweetDraft objects
        """
        valid_drafts = []
        attempts = 0
        max_attempts = 3

        while len(valid_drafts) < n and attempts < max_attempts:
            # Request more than needed to allow for filtering
            batch_size = (n - len(valid_drafts)) + 1

            prompt = self._build_prompt(
                content,
                source_url,
                allow_thread=allow_thread,
                suggest_image=suggest_image,
            )

            # If we are retrying, add a strong hint to be different
            if attempts > 0:
                prompt += "\n\nCRITICAL: The previous outputs were too similar to my past tweets. You MUST change the structure and opening hook completely."

            results = self.provider.generate_multiple(prompt, n=batch_size, max_tokens=800)

            for result in results:
                draft = self._parse_response(result.text, source_url)

                # Check for similarity
                if self._is_too_similar(draft.content):
                    continue

                # Check for duplicates within current batch
                if any(d.content == draft.content for d in valid_drafts):
                    continue

                valid_drafts.append(draft)
                if len(valid_drafts) >= n:
                    break

            attempts += 1

        # If we couldn't generate enough valid drafts, just return what we have
        # or fill with the last generated ones even if similar (better than nothing)
        if len(valid_drafts) < n and results:
            remaining = n - len(valid_drafts)
            for result in results[:remaining]:
                draft = self._parse_response(result.text, source_url)
                # Avoid exact duplicates in list
                if not any(d.content == draft.content for d in valid_drafts):
                    valid_drafts.append(draft)

        return valid_drafts[:n]

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

    def generate_from_topic(
        self,
        topic: str,
        allow_thread: bool = True,
        suggest_image: bool = True,
    ) -> TweetDraft:
        """Generate a tweet based on a general topic (no specific source)."""
        return self.generate_single(
            content=topic,
            source_url=None,
            allow_thread=allow_thread,
            suggest_image=suggest_image,
        )
