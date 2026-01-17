"""Reply generation using LLM with viral prompt framework."""

import logging

from twitter_bot.browser.watcher import ScrapedTweet
from twitter_bot.generation.provider import LLMProvider
from twitter_bot.state.manager import StateManager

logger = logging.getLogger(__name__)

# Available reply types for rotation
REPLY_TYPES = ["expert", "contrarian", "question", "story", "simplifier"]

# Instructions for each reply type
REPLY_TYPE_INSTRUCTIONS = {
    "expert": """Add ONE specific insight from your experience that extends their point.
Pattern: "[Agreement/validation] + [Your specific addition]"
Must include concrete detail (numbers, specific tech, real example).""",
    "contrarian": """Respectfully push back on ONE aspect while acknowledging the core point.
Pattern: "[Acknowledge merit] + but [your counterpoint] + [brief why]"
Not argumentative - thoughtful disagreement that sparks discussion.""",
    "question": """Ask ONE specific question that shows you understood AND thought deeper.
Pattern: "[Brief context] + [Specific question]?"
The question should make THEM think, not be easily answered.""",
    "story": """Share a 1-2 sentence personal experience that relates.
Pattern: "[What happened] + [What you learned]"
Must be specific (not "I once had this problem too").""",
    "simplifier": """Reframe their point more memorably in fewer words.
Pattern: "TL;DR: [their point distilled]" or "[Metaphor that captures it]"
Add a fresh angle they might not have considered.""",
}


class ReplyGenerator:
    """Generates viral replies using LLM."""

    def __init__(
        self,
        provider: LLMProvider,
        voice_profile: str,
        state: StateManager,
    ):
        """Initialize the reply generator.

        Args:
            provider: LLM provider for generation
            voice_profile: Voice/persona description for consistent tone
            state: StateManager for reply type rotation
        """
        self.provider = provider
        self.voice_profile = voice_profile
        self.state = state

    def generate_reply(self, tweet: ScrapedTweet) -> tuple[str, str]:
        """Generate a reply for a tweet.

        Args:
            tweet: The tweet to reply to

        Returns:
            Tuple of (reply_text, reply_type)
        """
        # Get next reply type from rotation
        reply_type = self.state.get_next_reply_type()

        # Build the prompt
        prompt = self._build_prompt(tweet, reply_type)

        # Generate reply
        logger.debug(f"Generating {reply_type} reply for tweet {tweet.tweet_id}")
        result = self.provider.generate(prompt, max_tokens=150)

        # Clean up the reply
        reply = self._clean_reply(result.text)

        # Validate length
        if len(reply) > 280:
            logger.warning(f"Reply too long ({len(reply)} chars), truncating")
            reply = reply[:277] + "..."

        logger.info(f"Generated {reply_type} reply: {reply[:50]}...")
        return reply, reply_type

    def _build_prompt(self, tweet: ScrapedTweet, reply_type: str) -> str:
        """Build the reply generation prompt.

        Args:
            tweet: The tweet to reply to
            reply_type: The type of reply to generate

        Returns:
            Complete prompt string
        """
        return f"""## CONTEXT
You are Maxime. 19. Bordeaux. Builder.

{self.voice_profile}

You're replying to this tweet:
---
@{tweet.author_handle}:
"{tweet.content}"
---
Engagement: {tweet.likes} likes, {tweet.retweets} RTs, {tweet.replies} replies

## YOUR MISSION
Write a reply that:
1. ADDS VALUE - Not "Great take!" but actual insight
2. STOPS THE SCROLL - First words must hook
3. SOUNDS LIKE YOU - Builder, direct, no corporate speak
4. DRIVES ENGAGEMENT - Makes people want to reply to YOU

## REPLY TYPE: {reply_type.upper()}

{REPLY_TYPE_INSTRUCTIONS[reply_type]}

## CONSTRAINTS
- MAX 200 characters (punchy wins)
- No hashtags ever
- No links
- No emojis unless absolutely natural
- No "I agree" or "This is so true"
- Sound like a 19-year-old builder, not LinkedIn

## BANNED PHRASES
- "Great post!", "Love this!", "So true!"
- "Game changer", "Level up", "Unlock"
- "This is the way", "Couldn't agree more"
- Starting with "I"
- Generic praise without substance

## YOUR ANGLE
Connect to YOUR expertise when relevant:
- AI/ML, LLMs, Claude, GPT
- Next.js, TypeScript, React, Python
- Self-Sovereign Identity, DIDs
- Indie hacking, shipping, building
- Parkour (discipline, risk, commitment)

## OUTPUT
Reply text only. No quotes. No explanation."""

    def _clean_reply(self, text: str) -> str:
        """Clean up LLM output.

        Args:
            text: Raw LLM output

        Returns:
            Cleaned reply text
        """
        text = text.strip()

        # Remove quotes if wrapped
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]

        # Remove any "Reply:" or similar prefix
        prefixes = ["reply:", "response:", "answer:"]
        for prefix in prefixes:
            if text.lower().startswith(prefix):
                text = text[len(prefix) :].strip()

        # Remove any trailing quotes or punctuation artifacts
        text = text.strip('"\'')

        return text.strip()
