"""Tweet generator using LLM provider and voice profile."""

import random
import re
from difflib import SequenceMatcher
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
SHORT_FORMATS = [
    "hot_take",
    "controversial",
    "one_liner",
    "unpopular_opinion",
    "observation",
]

THREAD_FORMATS = [
    "thread",
    "guide",
    "deep_dive",
    "story",
    "analysis",
]

STANDARD_FORMATS = [
    "insight",
    "question",
    "tip",
    "builder_update",
    "behind_scenes",
]

TWEET_FORMATS = SHORT_FORMATS + THREAD_FORMATS + STANDARD_FORMATS


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
        # We want to force variety: Short vs Thread vs Standard
        if allow_thread:
            # 30% chance of thread, 35% short, 35% standard
            roll = random.random()
            if roll < 0.3:
                category = "THREAD"
                suggested_format = random.choice(THREAD_FORMATS)
            elif roll < 0.65:
                category = "SHORT"
                suggested_format = random.choice(SHORT_FORMATS)
            else:
                category = "STANDARD"
                suggested_format = random.choice(STANDARD_FORMATS)
        else:
            # No threads allowed
            if random.random() < 0.5:
                category = "SHORT"
                suggested_format = random.choice(SHORT_FORMATS)
            else:
                category = "STANDARD"
                suggested_format = random.choice(STANDARD_FORMATS)

        # Add variety by rotating opening styles
        opening_styles = [
            "Start with a QUESTION that challenges assumptions",
            "Start with a PERSONAL STORY or anecdote (one sentence)",
            "Start with a BOLD CLAIM that's slightly controversial",
            "Start with CONCRETE NUMBERS or data",
            "Start with a SHORT observation (under 10 words), then expand",
            "Start by DISAGREEING with common advice",
            "Start with something you LEARNED today",
            "Start with a COMPARISON (X vs Y format)",
        ]
        selected_opening = random.choice(opening_styles)

        # Maxime-specific voice instructions
        prompt_parts.append(f"""## OPENING STYLE FOR THIS TWEET
**{selected_opening}**

## WHO YOU ARE

You're Maxime. 19. Bordeaux. You build shit.

**Your DNA:**
- **Builder vs Consumer**: You believe "The future belongs to those who create." You don't wait; you build.
- **Tech Stack**: Next.js, TypeScript, Python, K8s. You completed **Harvard CS50** while working full-time.
- **Professional**: 
  - **Verana**: Building the Trust Network & Visualizer.
  - **2060.io**: Built "Concieragent" (decentralized identity/DIDComm).
  - **Klyx**: CEO of your own web agency at 19.
- **Community & Sport**: 
  - Co-founder of **PKBA** (biggest parkour club in Nouvelle-Aquitaine, 60+ members).
  - Founder of **VertiFlow** (movement brand).
  - Active member of **GDG Bordeaux**.

**Your Philosophy:**
- Parkour taught you more about risk management and discipline than any business book.
- You balance deep tech (SSI, Cryptography) with real-world action (Parkour, Agency work).
- You are young (19) but you're already leaving a trace.

## YOUR VIRAL PLAYBOOK (STRICTLY FOLLOW THIS)

You don't write "updates". You engineer viral assets using these proven frameworks:

1. **The E.H.A. Framework** (MANDATORY):
   - **Emotion**: Trigger high-arousal emotions (Awe, Curiosity, Anger/Debate). Avoid "contentment".
   - **Hook**: First line MUST stop the scroll. 
   - **Action**: Every tweet needs a purpose (teach, provoke, or inspire).

2. **The "You" Rule**:
   - Use Second-Person Language.
   - Bad: "Developers should learn rust."
   - Good: "You need to learn Rust if you want to stay relevant."

3. **Viral Sentence Patterns (STEAL THESE)**:
       - **The Binary**: "Most people do X. The winners do Y."
      - **The Data Flex**: "I analyzed 1,000 repos. Here's what I found:"
      - **The Time Frame**: "How to build an MVP in 48 hours (not 4 weeks)."
      - **The Contrarian**: "Everyone says X. They're wrong. Here's why."
      - **The Transformation**: "At 16, I was broke. At 19, I run an agency. The blueprint:"
   
   ## YOUR TWEET STYLE
   
   VARIETY is key. You don't sound like a bot. You mix up:
   
   **The Challenger (Attack BS ideas)**:
   - "Stop romanticizing complexity. If you can't explain it to a 5-year-old, you don't understand it."
   - "Everyone is building AI wrappers. The real money is in the shovels (infrastructure)."
   
   **The Guide (Offer a lens/fix)**:
   - "Here’s my 3-part framework for shipping features fast. Steal it."
   - "The best way to learn React? Build a clone of a tool you use every day."
   
   **The Micro-Story (Before -> After -> Lesson)**:
   - "At 16, I failed my first startup. At 19, I run an agency. The difference? I stopped overthinking and started shipping."
   - "Spent 3 days debugging a race condition. It was a single line of config. Lesson: Read the docs first."
   
   **The "Observation" (Relatable & Insightful)**:
   - "Parkour taught me: you either commit to the jump or you don't. Same with shipping code."
   - "Most auth is broken because we trust servers, not users. That's why I'm building Concieragent."
   
   ## RULES
   
   1. **Clarity > Cleverness**. Simple words. Short sentences.
   2. **Specifics > Generics**. Use real numbers (lines of code, hours, dollars).
   3. **Sound like a 19-year-old builder**. No corporate speak.
   4. **Take Stances on CONCEPTS, not PRODUCTS**. 
      - Good: "Static typing saves time." (Concept)
      - Bad: "You must use TypeScript or you will fail." (Hype)
   5. **No Hashtags**. Never.
   
   ## BANNED (instant cringe)

   - "game changer", "level up", "unlock your potential"
   - "imagine if", "what if I told you", "here's the thing"
   - "revolution", "beast", "insane", "wild" (unless ironic)
   - "ahead of the curve", "left behind", "getting left behind", "FOMO"
   - "You're about to witness", "You're about to unlock"
   - "This proves that", "This kills the old way"
   - "I've spent months digging", "Here's what I found"
   - "The best part?", "But here's the catch"
   - "What's your next move?", "Who's with me?"
   - Anything a LinkedIn influencer would say
   - Excessive emojis (one or zero max, and only if natural)
   - Hashtags (never)
   - "Let me explain:", "Thread:", "1/n"
   - Generic motivational crap
   - Starting with "Just" or "So"
   - Summarizing the article like a news bot ("Just read an interesting article about...")
   - Sounding like an ad ("This tool is amazing!"). Critiques > Praise.
   
   ## FORMAT SUGGESTION FOR THIS TWEET: {suggested_format.upper()}
   
   """)

        # Add constraints based on category
        if category == "SHORT":
            prompt_parts.append("""
**CONSTRAINT: SHORT & PUNCHY**
- Maximum 140 characters.
- No filler words. 
- One single, powerful thought or question.
- Do NOT use bullet points.
""")
        elif category == "THREAD":
            prompt_parts.append("""
**CONSTRAINT: EDUCATIONAL THREAD**
- This must be a **THREAD** (multiple tweets).
- Go DEEP. Teach something specific.
- Structure: Hook -> Context -> Step-by-Step -> Outcome.
""")

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

        # Thread option instructions
        if category == "THREAD":
            thread_instruction = """
**THREAD STRUCTURE**:
1. **The Hook**: Bold statement + Benefit. (e.g., "I spent 50 hours on X. Here is what I learned.")
2. **The Meat**: Break down the concept into 3-4 actionable steps/insights.
3. **The Cliffhangers**: End middle tweets with "open loops" (e.g., "But here's the catch...", "The best part?").
4. **The Conclusion**: Summary + Call to Action.
"""
        else:
            thread_instruction = "**SINGLE TWEET ONLY.** Do not write a thread."

        # Image suggestion
        image_instruction = ""
        if suggest_image:
            image_instruction = """
**IMAGE SUGGESTION**: If a meme, chart, or code snippet would make this viral, add:
[IMAGE: brief description. e.g., "Drake meme comparing X and Y" or "Chart showing growth curve"]
"""

        # Final instruction
        prompt_parts.append(f"""## YOUR TASK

Use the SOURCE CONTEXT as raw material.
**CRITICAL**: Do NOT summarize.
Instead, Pivot:
- "This proves..."
- "I've been saying this for months..."
- "Here is the code implication..."
- "This kills the old way of..."

Identify the core topic.
{thread_instruction}
{image_instruction}

Write a tweet (or thread) that:
- Fits the constraints above ({category} format)
- Uses the **E.H.A. Framework**
- Uses **Second-Person ("You")** language
- Takes a **Strong, Binary Stance**

IMPORTANT: Do NOT force an SSI (Self-Sovereign Identity) angle unless the source is explicitly about identity.

Output ONLY the tweet text (or THREAD: format). No quotes. No explanation.""")

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

            # Truncate each part at word boundary
            thread_parts = [self._truncate_at_word_boundary(p, 280) for p in thread_parts]

            # Main content is the first tweet
            content = thread_parts[0] if thread_parts else text
        else:
            content = text
            # Truncate at word boundary if over 280
            if len(content) > 280:
                content = self._truncate_at_word_boundary(content, 280)

        return TweetDraft(
            content=content,
            source_url=source_url,
            is_thread=is_thread,
            thread_parts=thread_parts,
            suggested_image=suggested_image,
        )

    # Overused phrases to detect and reject
    OVERUSED_PATTERNS = [
        r"you're about to witness",
        r"you're about to unlock",
        r"this proves that",
        r"this kills the old way",
        r"you're either .+ or getting left behind",
        r"getting left behind",
        r"ahead of the curve",
        r"i've spent months digging",
        r"here's what i found",
        r"the best part\?",
        r"but here's the catch",
        r"what's your next move",
        r"who's with me\?",
        r"let me explain",
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
