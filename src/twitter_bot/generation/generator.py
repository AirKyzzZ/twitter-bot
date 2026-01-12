"""Tweet generator using LLM provider and voice profile."""

import random
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
   - "ahead of the curve", "left behind", "FOMO"
   - Anything a LinkedIn influencer would say
   - Excessive emojis (one or zero max, and only if natural)
   - Hashtags (never)
   - "Let me explain:", "Thread:", "1/n"
   - Generic motivational crap
   - Starting with "Just" or "So"
   - Summarizing the article like a news bot ("Just read an interesting article about...")
   - Sounding like an ad ("This tool is amazing!"). Critiques > Praise.
   
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
        prompt_parts.append(f"""## SOURCE CONTEXT
{content[:2000]}
""")

        if source_url:
            prompt_parts.append(f"Source: {source_url}\n")

        # Thread option
        thread_instruction = ""
        if allow_thread:
            thread_instruction = """
**THREAD OPTION (VIRAL STRUCTURE)**: 
If the content is deep (tutorial, big insight, story), write a **5-7 tweet thread**.
Thread Structure:
1. **The Hook**: Bold statement + Benefit. (e.g., "I spent 50 hours on X. Here is what I learned.")
2. **The Meat**: Break down the concept into 3-4 actionable steps/insights.
3. **The Cliffhangers**: End middle tweets with "open loops" (e.g., "But here's the catch...", "The best part?").
4. **The Conclusion**: Summary + Call to Action.

Only use threads for substantial content. Most tweets should be single.
"""

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
- Fits within 280 characters (per tweet)
- Uses the **E.H.A. Framework**
- Uses **Second-Person ("You")** language
- Takes a **Strong, Binary Stance**

IMPORTANT: Do NOT force an SSI (Self-Sovereign Identity) angle unless the source is explicitly about identity.

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

    def _is_too_similar(self, content: str, threshold: float = 0.6) -> bool:
        """Check if content is too similar to recent tweets."""
        for past_tweet in self.recent_tweets:
            ratio = SequenceMatcher(None, content, past_tweet).ratio()
            if ratio > threshold:
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
            content: Source content to transform into tweets
            source_url: Optional URL of the source
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
